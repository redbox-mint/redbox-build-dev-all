import re
from java.util import Date, HashMap, ArrayList
from java.lang import String, Integer, Long
from java.security import SecureRandom
from java.net import URLDecoder, URLEncoder
from java.io import File
from com.googlecode.fascinator.common.storage import StorageUtils
from com.googlecode.fascinator.spring import ApplicationContextProvider
from com.googlecode.fascinator.common import BasicHttpClient
from org.apache.commons.httpclient.methods import GetMethod
from com.googlecode.fascinator.common import JsonSimple
from org.apache.commons.io import FileUtils
from com.googlecode.fascinator.common import FascinatorHome

class CurationData():
    def __init__(self):
        pass

    def __activate__(self, context):
        self.None = context["log"]
        self.systemConfig = context["systemConfig"]
        self.sessionState = context["sessionState"]
        self.response = context["response"]
        self.request = context["request"]
        self.services = context["Services"]

        self.sessionState.set("username", "admin")
        self.writer = self.response.getPrintWriter("text/plain; charset=UTF-8")

        curationJobDao = ApplicationContextProvider.getApplicationContext().getBean("curationJobDao")
        publicationHandler = ApplicationContextProvider.getApplicationContext().getBean("publicationHandler")
        jobs = JsonSimple(File(FascinatorHome.getPath() + "/curation-status-responses/inProgressJobs.json")).getArray("inProgressJobs")
        self.writer.println(jobs.size())


        for curationJob in jobs:
            curationJob
            jobStatus = self.queryJobStatus(curationJob)
            self.writer.println(jobStatus.toString())
            status = jobStatus.getString("failed", "status")
            self.writeResponseToStatusResponseCache(jobStatus.getInteger(None, "job_id"), jobStatus)
            self.writer.println(status)
            if "complete" == status:
                publicationHandler.publishRecords(jobStatus.getArray("job_items"))
                self.updateLocalRecordRelations(jobStatus.getArray("job_items"))
           
            self.writer.close()
            self.sessionState.remove("username")

    def queryJobStatus(self, curationJob):
        relations = ArrayList()
        get = None
        try:
            url = self.systemConfig.getString(None, "curation", "curation-manager-url")

            client = BasicHttpClient(url + "/job/" + curationJob)
            get = GetMethod(url + "/job/" + curationJob)
            client.executeMethod(get)
            status = get.getStatusCode()
            if status != 200:
                text = get.getStatusText()
                self.log.error(String.format("Error accessing Curation Manager, status code '%d' returned with message: %s", status, text));
                return None;

        except Exception, ex:

            return None;


        # Return our results body
        response = None;
        try:
            response = get.getResponseBodyAsString();
        except Exception, ex:
            self.log.error("Error accessing response body: ", ex);
            return None;


        return JsonSimple(response);

    def updateLocalRecordRelations(self, jobItems):
        oidIdentifierMap = HashMap()
        for jobItem in jobItems:
            oidIdentifierMap.put(jobItem.get("oid"),jobItem.get("required_identifiers")[0].get("identifier"))
            
        for jobItem in jobItems:
            type = jobItem.get("type");
            targetSystem = systemConfig.getString(null, "curation", "supported-types", type);
            if targetSystem == "redbox":
                oid = jobItem.get("oid")
                digitalObject = StorageUtils.getDigitalObject(self.services.getStorage(), oid)
                tfPackagePid = self.getPackageData(digitalObject)
                metadataJsonPayload = digitalObject.getPayload(tfPackagePid)
                metadataJsonInstream = metadataJsonPayload.open()
                metadataJson = JsonSimple(metadataJsonInstream)
                metadataJsonPayload.close()
                relationships = metadataJson.getArray("relationships")
                if relationships is not None:
                    for relationship in relationships:
                        if relationship.get("system") != "redbox" or relationship.get("system") != None:
                            url = self.systemConfig.getString(None, "curation","external-system-urls","notify-curation",system)
                            
                            client = BasicHttpClient(url+ "&identifier="+relationship.get("identifier"))
                            get = GetMethod(url+ "&identifier="+relationship.get("identifier"))
                            client.executeMethod(get)
                            if get.getStatusCode() == 200:
                                response = JsonSimple(get.getResponseBodyAsString())
                                relationship.put("curatedPid",oidIdentifierMap.get(response.getString(None,"oid")))
                                relationship.put("isCurated",True)
                            
                            #Now update the relationship on Mint's side
                            break
                    
        istream = ByteArrayInputStream(String(metadataJson.toString(True)).getBytes())
        StorageUtils.createOrUpdatePayload(digitalObject,tfPackagePid,istream)
                
                
    def getPackageData(self,object):
        try:
            pidList = object.getPayloadIdList()
            for pid in pidList:
                if pid.endswith("tfpackage"):
                    return pid
        except StorageException:
            self.log.error("Error accessing object PID list for object '{}' ", self.oid)
            return
        return None     
        
    def writeResponseToStatusResponseCache(self, jobId, jobStatus):
        curationStatusRespones = File(FascinatorHome.getPath() + "/curation-status-responses")
        if curationStatusRespones.exists():
            FileUtils.forceMkdir(curationStatusRespones)

        FileUtils.writeStringToFile(File(curationStatusRespones.getPath() + "/" + Integer(jobId).toString() + ".json"), jobStatus.toString(True))
