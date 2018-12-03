import xml

from com.googlecode.fascinator.api.indexer import SearchRequest
from com.googlecode.fascinator.common import JsonObject
from com.googlecode.fascinator.common.messaging import MessagingServices
from com.googlecode.fascinator.common.solr import SolrResult
from com.googlecode.fascinator.messaging import TransactionManagerQueueConsumer
from com.yourmediashelf.fedora.client import FedoraClient
from com.yourmediashelf.fedora.client import FedoraCredentials
from com.yourmediashelf.fedora.util import XmlSerializer
from java.io import ByteArrayInputStream
from java.io import ByteArrayOutputStream
from java.io import InputStreamReader
from java.lang import Exception
from java.lang import String
from org.dom4j import DocumentFactory
from org.dom4j.io import SAXReader


class VitalData:
    def __init__(self):
        self.messaging = MessagingServices.getInstance()

    def __activate__(self, context):
        self.vc = context
        self.log      = self.vc["log"]
        self.services = self.vc["Services"]
        self.writer   = self.vc["response"].getPrintWriter("text/html; charset=UTF-8")
        # We check config now for how to store this
        self.config   = self.vc["systemConfig"]
        self.pidProperty = self.config.getString("vitalHandle", ["curation", "pidProperty"])

        # Working variables
        self.fedoraUrl = None
        self.docFactory = None
        self.saxReader = None

        self.process()

    def process(self):
        self.log.debug("VITAL housekeeping executing")

        # Find solr records
        result = self.search_solr()
        if result is None:
            return

        # Is there any work to do?
        num = result.getNumFound()
        if num == 0:
            self.writer.println("No records to process")
            self.writer.close()
            return

        # Time to connect to fedora
        fedora = self.fedora_connect()
        if fedora is None:
            return

        # Now loop through each object and process
        for record in result.getResults():
            success = self.process_record(record, fedora)
            if not success:
                return

        self.writer.println("%s record(s) processed" % num)
        self.writer.close()

    # Process an individual record
    def process_record(self, record, fedora):
        try:
            # Get the object from storage
            id = record.getFirst("storage_id")
            object = self.services.getStorage().getObject(id)

            # And get its metadata
            metadata = object.getMetadata()
            vitalPid = metadata.getProperty("vitalPid")
            pidProperty = metadata.getProperty(self.pidProperty)
            self.log.debug("Object '{}' has pidProperty '{}'", id, pidProperty)

            # Bug here: ReDBox always reindex Vital, even if not updated
            if not pidProperty is None:
                self.log.debug("Object '{}', pidProperty '{}' has already been published. Ignore.", id, pidProperty)
                return True

            if vitalPid is None:
                self.log.error("Object '{}' has invalid VITAL data", id)
                self.throw_error("Object '%s' has invalid VITAL data" % id)
                return False

            # Get handle in DC datastream from VITAL
            vitalHandle = self.get_handle(fedora, vitalPid)
            if vitalHandle is None:
                # Finish with failed access
                return False
            if vitalHandle == "NONE":
                # Finish with no error, but no handle (yet)
                self.log.debug("Object '{}', in VITAL '{}' has no handle yet", id, vitalPid)
                return True

            # We have a valid handle now, write to the object
            metadata.setProperty(self.pidProperty, vitalHandle)
            object.close()

            # Transform the object, to update our payloads
            #transformer = PluginManager.getTransformer("jsonVelocity")
            #transformer.init(JsonSimpleConfig.getSystemFile())
            #transformer.transform(object, "{}")

            # Re-index... avoids showing up in this script again
            #self.services.getIndexer().index(id)
            #self.services.getIndexer().commit()

            # Finally send a message to the VITAL subscriber
            self.send_message(id)

            # Simple debugging
            self.log.debug("Processing: '{}' <= '{}'", vitalPid, id)
            self.log.debug("Handle: '{}'", vitalHandle)
            return True

        except Exception, e:
            self.log.error("Error updating object: ", e)
            self.throw_error("failure updating object: " + e.getMessage())
            return False

    # Send an event notification
    def send_message(self, oid):
        message = JsonObject()
        message.put("oid", oid)
        message.put("eventType", "ReIndex")
        message.put("username", "system")
        message.put("context", "Workflow")
        message.put("task", "workflow")
        message.put("quickIndex", True)
        self.messaging.queueMessage(
            TransactionManagerQueueConsumer.LISTENER_ID,
            message.toString())

    # Get the handle for the PID from VITAL, if set
    def get_handle(self, fedora, vitalPid):
        try:
            response = FedoraClient.getObjectXML(vitalPid).execute(fedora)
            self.log.info("handle response status: %s" % response.getStatus())

            inStream = response.getEntityInputStream()
            outStream = ByteArrayOutputStream()
            XmlSerializer.canonicalize(inStream, outStream)
            responseAsString = str(String(outStream.toByteArray()))
            self.log.debug("response: %s" % responseAsString)

            DOMTree = xml.dom.minidom.parseString(responseAsString)
            digitalObject = DOMTree.documentElement
            if digitalObject is None:
                return None
            handleDomain = self.config.getString("hdl.handle.net",
                                                 ["transformerDefaults", "vital", "server", "publishedDomain"])

            dcIds = digitalObject.getElementsByTagName('dc:identifier')
            for dcId in dcIds:
                self.log.debug("found dc:identifier: %s" % str(dcId.toxml()))
                dcIdValue = str(dcId.firstChild.nodeValue)
                self.log.debug("dc Id value: %s" % dcIdValue)
                if dcIdValue.find(handleDomain) != -1:
                    return dcIdValue
            return "NONE"

        except Exception, e:
            self.log.error("Error fetching datastream: ", e)
            self.throw_error("failure fetching datastream: %s" % e.getMessage())
            return None

    # Parse and read an XML document
    def parse_xml(self, inputStrem):
        try:
            # First document in the list should run these
            if self.docFactory is None:
                self.docFactory = DocumentFactory()
            if self.saxReader is None:
                self.saxReader = SAXReader(self.docFactory)

            # The actual parsing
            reader = InputStreamReader(inputStrem, "UTF-8")
            return self.saxReader.read(reader)
        except Exception, e:
            self.log.error("Error parsing XML: ", e)
            self.throw_error("failure parsing XML: " + e.getMessage())
            return None

    # Connect to fedora and test access before returning
    def fedora_connect(self):
        # Read our configuration
        self.fedoraUrl = self.config.getString(None, ["transformerDefaults", "vital", "server", "url"])
        fedoraUsername = self.config.getString(None, ["transformerDefaults", "vital", "server", "username"])
        fedoraPassword = self.config.getString(None, ["transformerDefaults", "vital", "server", "password"])
        fedoraTimeout = self.config.getInteger(15, ["transformerDefaults", "vital", "server", "timeout"])
        if (self.fedoraUrl is None) or \
                (fedoraUsername is None) or (fedoraPassword is None):
            self.log.error("Invalid VITAL configuration!")
            self.throw_error("Invalid VITAL configuration!")
            return None

        # Establish and test the connection
        try:
            fedora = FedoraClient(FedoraCredentials(self.fedoraUrl, fedoraUsername, fedoraPassword))
            # Cannot set socket timeout with yourshelf client
            # fedoraClient.SOCKET_TIMEOUT_SECONDS = fedoraTimeout
            return fedora
        except Exception, e:
            self.log.error("Error connecting to Fedora: ", e)
            self.throw_error("connecting to Fedora failed: " + e.getMessage())
            return None

    # Search solr for objects that have
    def search_solr(self):
        # Build our solr query
        namespace = self.config.getString("changeme", ["transformerDefaults", "vital", "server", "namespace"])
        vitalPidExists = "vitalPid:%s*" % namespace
        vitalHandleExists = "pidProperty:http*"
        query = vitalPidExists + " AND NOT " + vitalHandleExists
        # Prepare the query
        req = SearchRequest(query)
        req.setParam("facet", "false")
        req.setParam("rows", "100")
        # Run the query
        try:
            out = ByteArrayOutputStream()
            self.services.getIndexer().search(req, out)
            return SolrResult(ByteArrayInputStream(out.toByteArray()))
        except Exception, e:
            self.log.error("Error searching solr: ", e)
            self.throw_error("failure searching solr: " + e.getMessage())
            return None

    def throw_error(self, message):
        self.vc["response"].setStatus(500)
        self.writer.println("Error: " + message)
        self.writer.close()
