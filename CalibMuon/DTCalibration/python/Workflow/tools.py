import os,sys,imp
import ConfigParser

def replaceTemplate(template,**opts):
    result = open(template).read()
    for item in opts:
         old = '@@%s@@'%item
         new = str(opts[item])
         print "Replacing",old,"to",new
         result = result.replace(old,new)

    return result
 
def listFilesInCastor(castor_dir,type = 'root',prefix = 'rfio:'):
    if not castor_dir: raise ValueError,'Please specify valid castor dir'

    from subprocess import Popen,PIPE
    p1 = Popen(['nsls',castor_dir],stdout=PIPE)
    #p2 = Popen(['grep',type],stdin=p1.stdout,stdout=PIPE)
    #files = [prefix + castor_dir + "/" + item[:-1] for item in p2.stdout]
    #p2.stdout.close()
    files = [ "%s%s/%s" % (prefix,castor_dir,item.rstrip()) for item in p1.stdout if item.find(type) != -1 ] 
    p1.stdout.close()
    return files

def listFilesLocal(dir,type = 'root'):
    if not dir: raise ValueError,'Please specify valid dir'

    #from subprocess import Popen,PIPE
    #p1 = Popen(['ls',dir],stdout=PIPE)
    #p2 = Popen(['grep',type],stdin=p1.stdout,stdout=PIPE)
    #files = [dir + "/" + item[:-1] for item in p2.stdout]
    #p2.stdout.close()
    files = os.listdir(dir)
    files = [ "%s/%s" % (dir,item) for item in files if item.find(type) != -1 ]

    return files

def haddInCastor(castor_dir,result_file,type = 'root',prefix = 'rfio:',suffix = None):
    if not castor_dir: raise ValueError,'Please specify valid castor dir'
    if not result_file: raise ValueError,'Please specify valid output file name'

    #cmd = 'hadd %s `./listfilesCastor %s | grep %s`'%(result_file,castor_dir,type)
    #print "Running",cmd
    #os.system(cmd)
    from subprocess import call
    files = listFilesInCastor(castor_dir,type,prefix)
    if suffix: files = [item + suffix for item in files]
 
    cmd = ['hadd',result_file]
    cmd.extend(files)
    #print cmd
    retcode = call(cmd)
    return retcode

def haddLocal(dir,result_file,type = 'root'):
    if not dir: raise ValueError,'Please specify valid dir'
    if not result_file: raise ValueError,'Please specify valid output file name'

    from subprocess import call
    files = listFilesLocal(dir,type)
    cmd = ['hadd',result_file]
    cmd.extend(files)
    #print cmd
    retcode = call(cmd)
    return retcode

def setGridEnv(cmssw_dir):
    cwd = os.getcwd()
    os.chdir(cmssw_dir)

    os.system('source /afs/cern.ch/cms/LCG/LCG-2/UI/cms_ui_env.sh')
    os.system('cmsenv')
    os.system('source /afs/cern.ch/cms/ccs/wm/scripts/Crab/crab.sh')
 
    os.chdir(cwd)
 
    return

def parseInput(inputFields,requiredFields = ()):

    class options: pass
    for item in sys.argv:
        option = item.split('=')[0]
        if option in inputFields:
            value = item.split('=')[1]
            if value in ('true','True','yes','Yes'): value = True
            elif value in ('false','False','no','No'): value = False

            setattr(options,option,value)

    for item in requiredFields:
        if not hasattr(options,item):
            raise RuntimeError,'Need to set "%s"' % item

    return options

def loadCmsProcess(psetName):
    pset = imp.load_source("psetmodule",psetName)
    return pset.process

def prependPaths(process,seqname):
    for path in process.paths: 
        getattr(process,path)._seq = getattr(process,seqname)*getattr(process,path)._seq

def writeCfg(process,dir,psetName):
    if not os.path.exists(dir): os.makedirs(dir)
    open(dir + '/' + psetName,'w').write(process.dumpPython())

def loadCrabCfg(cfgName=None):
    config = ConfigParser.ConfigParser()
    if cfgName: config.read(cfgName)
    return config

def loadCrabDefault(crabCfg,config):
    # CRAB section
    if not crabCfg.has_section('CRAB'): crabCfg.add_section('CRAB')
    crabCfg.set('CRAB','jobtype','cmssw')
    crabCfg.set('CRAB','scheduler',config.scheduler) 
    if config.useserver: crabCfg.set('CRAB','use_server',1)

    # CMSSW section
    if not crabCfg.has_section('CMSSW'): crabCfg.add_section('CMSSW')
    crabCfg.set('CMSSW','datasetpath',config.datasetpath)
    crabCfg.set('CMSSW','pset','pset.py')

    # Splitting config
    crabCfg.remove_option('CMSSW','total_number_of_events')
    crabCfg.remove_option('CMSSW','events_per_job')
    crabCfg.remove_option('CMSSW','number_of_jobs')
    crabCfg.remove_option('CMSSW','total_number_of_lumis')
    crabCfg.remove_option('CMSSW','lumis_per_job')
    crabCfg.remove_option('CMSSW','lumi_mask')
    crabCfg.remove_option('CMSSW','split_by_run')
 
    crabCfg.set('CMSSW','runselection',config.runselection)
    """
    if hasattr(config,'totalnumberevents'): crabCfg.set('CMSSW','total_number_of_events',config.totalnumberevents)
    if hasattr(config,'eventsperjob'): crabCfg.set('CMSSW','events_per_job',config.eventsperjob) 
    """
    if hasattr(config,'splitByLumi') and config.splitByLumi:
        crabCfg.set('CMSSW','total_number_of_lumis',config.totalnumberlumis)
        crabCfg.set('CMSSW','lumis_per_job',config.lumisperjob)
        if hasattr(config,'lumimask') and config.lumimask: crabCfg.set('CMSSW','lumi_mask',config.lumimask)
    else:
        crabCfg.set('CMSSW','split_by_run',1)
 
    # USER section
    if not crabCfg.has_section('USER'): crabCfg.add_section('USER')  

    # Stageout config
    if hasattr(config,'stageOutCAF') and config.stageOutCAF:
        crabCfg.set('USER','return_data',0)                
        crabCfg.set('USER','copy_data',1)  
        crabCfg.set('USER','storage_element','T2_CH_CAF')
        crabCfg.set('USER','user_remote_dir',config.userdircaf)
        crabCfg.set('USER','check_user_remote_dir',0)
    elif hasattr(config,'stageOutLocal') and config.stageOutLocal:
        crabCfg.set('USER','return_data',1)                
        crabCfg.set('USER','copy_data',0)
        crabCfg.remove_option('USER','storage_element')
        crabCfg.remove_option('USER','user_remote_dir')
        crabCfg.remove_option('USER','check_user_remote_dir')

    if hasattr(config,'email') and config.email: crabCfg.set('USER','eMail',config.email)
    crabCfg.set('USER','xml_report','crabReport.xml')

    if hasattr(config,'runOnGrid') and config.runOnGrid:
        crabCfg.remove_section('CAF')

    return crabCfg
