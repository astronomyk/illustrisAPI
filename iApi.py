import requests
import numpy as np
import h5py
import changeUnits

baseUrl = 'http://www.illustris-project.org/api/'
headers = {"api-key":"WELLTHISDOESNTSEEMRIGHT"}
    
# Routine to pull data from online
def get(path, params=None, fName='temp'): # gets data from url, saves to file
    # make HTTP GET request to path
    if (len(headers['api-key'])!=32):
        print("Have you put in your API key? This one isn't working")
        print('Currently it is: ',headers['api-key'])
        print('You can find your API key on the Illustris website:')
        print('http://www.illustris-project.org/data/')
        print('and update it in this program using')
        print("iApi.headers['api-key']='*MYAPIKEY*'")
        print("Or permanently change it in iApi.py")
    r = requests.get(path, params=params, headers=headers)
    
    # raise exception if response code is not HTTP SUCCESS (200)
    r.raise_for_status()

    if r.headers['content-type'] == 'application/json':
        return r.json() # parse json responses automatically

    dataFile=fName+'.hdf5'
    # Saves to file, currently disabled
    if 'content-disposition' in r.headers:
        filename = r.headers['content-disposition'].split("filename=")[1]
        with open(dataFile, 'wb') as f:
            f.write(r.content)
        return dataFile # return the filename string

    return r
    
# For a chosen galaxy pulls out all the particle data for a set of fields
particleTypeNames=['gas','dm','error','tracers','stars','bhs'] 
def getGalaxy(whichGalaxy, fields, # index of a galaxy and the 2d list of fields (particle type and name of fields)
        simulation='Illustris-1', snapshot=135, # which simulation and snapshot
        fileName='tempGal',rewriteFile=1, # name of the file where .hdf5 data is stored and whether to rewrite or just read
        getHalo=0): # can also pull out all data from halo (rather than subhalo) BIG!
    
    
    fields=np.array(fields) # converts to array
    order=np.argsort(fields[:,0])
    disorder=np.argsort(order) # needed to unsort the fields later...
    fields=fields[order,:] # orders by particle type
    nFields=order.size
    
    if rewriteFile==1: # redownloads file from the internet
        url='http://www.illustris-project.org/api/'+simulation+'/snapshots/'+str(snapshot)+'/subhalos/'+str(whichGalaxy)+'/cutout.hdf5?'
        if getHalo==1:
            url='http://www.illustris-project.org/api/'+simulation+'/snapshots/'+str(snapshot)+'/halos/'+str(whichGalaxy)+'/cutout.hdf5?'
        
        thisParticle=0
        thisEntry=0
        firstParticle=1
        while thisParticle<6: # cycles through all particle type

            if (int(fields[thisEntry,0])!=thisParticle): # checks there is at least one field for this particle
                thisParticle+=1
                continue
            if firstParticle==1: # first particle requires no ampersand
                firstParticle=0
            else: # all later particles do
                url+='&' 
            url+=particleTypeNames[thisParticle]+'=' # adds the name of the particle type
        
            firstEntry=1
            while int(fields[thisEntry,0])==thisParticle:
                if firstEntry==1: #first entry requires no comma
                    firstEntry=0
                else: # all later entries do
                    url+=','
                url+=fields[thisEntry,1] # adds every associated field
                thisEntry+=1
                if thisEntry==nFields:
                    break
            if thisEntry==nFields:
                break
            thisParticle+=1
        dataFile=get(url,fName=fileName)
    # end of "if rewriteFile==1:"
    if rewriteFile == 0: # if we're not redownloading need to set path to the file
        dataFile=fileName+'.hdf5'
    
    # gets a dictionary for unit conversions
    units=changeUnits.makeParticleDict(simulation=simulation,snapshot=snapshot)
    
    # actually get the data (saved to .hdf5 file)
    data=[] # initially empty list that we will fill up with the data
    with h5py.File(dataFile,'r') as f:
        for i in range(disorder.size):
            thisField=fields[disorder[i],:] # ensures data returned in original order of fields
            data.append(units[thisField[1]]*np.array(f['PartType'+thisField[0]][thisField[1]]))
            # returns all particle data of each field as a numpy array
    return data # returns all the particle fields as a list of numpy arrays in the same order as initial fields

# data from one field for all subhalos in a given snapshot  
def getSubhaloField(field,simulation='Illustris-1',snapshot=135,fileName='tempCat',rewriteFile=1):
    if rewriteFile==1: # redownloads file from the internet
        url='http://www.illustris-project.org/api/'+simulation+'/files/groupcat-'+str(snapshot)+'/?Subhalo='+field
        dataFile=get(url,fName=fileName)
    if rewriteFile == 0: # if we're not redownloading need to set path to the file
        dataFile=fileName+'.hdf5'
        
    with h5py.File(dataFile,'r') as f:
        data=np.array(f['Subhalo'][field])
    units=changeUnits.makeSubhaloDict(simulation=simulation,snapshot=snapshot)
    return data*units[field]
    
# data from one field for all halos in a given snapshot    
def getHaloField(field,simulation='Illustris-1',snapshot=135,fileName='tempCat',rewriteFile=1):
    if rewriteFile==1: # redownloads file from the internet
        url='http://www.illustris-project.org/api/'+simulation+'/files/groupcat-'+str(snapshot)+'/?Group='+field
        dataFile=get(url,fName=fileName)
    if rewriteFile == 0: # if we're not redownloading need to set path to the file
        dataFile=fileName+'.hdf5'
        
    with h5py.File(dataFile,'r') as f:
        data=np.array(f['Group'][field])
    units=changeUnits.makeHaloDict(simulation=simulation,snapshot=snapshot)
    return data*units[field]
    
#returns a dictionary with all halo catalog data corresponding to a particular halo
def getHaloData(whichHalo, simulation='Illustris-1', snapshot=135):
    units=changeUnits.makeHaloDict(simulation=simulation,snapshot=snapshot)
    url='http://www.illustris-project.org/api/'+simulation+'/snapshots/'+str(snapshot)+'/halos/'+str(whichHalo)+'/info.json'
    data=get(url)
    haloData=data['Group']
    haloKeys=list(haloData.keys())
    for i in range(len(haloKeys)):
        oldValue=np.array(haloData[haloKeys[i]])
        convFactor=units[haloKeys[i]]
        haloData[haloKeys[i]]=convFactor*oldValue
    return haloData
    
#returns a dictionary with all subhalo catalog data corresponding to a particular subhalo, plus progenitors!
def getSubhaloData(whichSubhalo, simulation='Illustris-1', snapshot=135):
    units=changeUnits.makeSubhaloDict(simulation=simulation,snapshot=snapshot)
    infoUrl='http://www.illustris-project.org/api/'+simulation+'/snapshots/'+str(snapshot)+'/subhalos/'+str(whichSubhalo)+'/info.json'
    infoData=get(infoUrl)
    subhaloData=infoData['Subhalo']
    subhaloKeys=list(subhaloData.keys())
    for i in range(len(subhaloKeys)):
        oldValue=np.array(subhaloData[subhaloKeys[i]])
        convFactor=units[subhaloKeys[i]]
        subhaloData[subhaloKeys[i]]=convFactor*oldValue
    return subhaloData
    
#returns the merger tree of a specified subhalo at some snapshot (UNFINISHED! Currently only works for z=0 snapshots!)
def oldGetTree(whichSubhalo, simulation='Illustris-1', snapshot=135):
    treeUrl='http://www.illustris-project.org/api/'+simulation+'/snapshots/'+str(snapshot)+'/subhalos/'+str(whichSubhalo)+'/sublink/mpb.hdf5'
    treeData=get(treeUrl,fName='tempTree')
    with h5py.File(treeData,'r') as f:
        treeSubs=f['SubfindID'][:]
        treeSnaps=f['SnapNum'][:]
    return treeSnaps,treeSubs
    
#returns the merger tree of a specified subhalo at some snapshot
def getTree(whichSubhalo, simulation='Illustris-1', snapshot=135):
    treeUrl='http://www.illustris-project.org/api/'+simulation+'/snapshots/'+str(snapshot)+'/subhalos/'+str(whichSubhalo)+'/sublink/simple.json'
    treeData=get(treeUrl)
    treeData['Main']=np.array(treeData['Main']) #don't know why these are lists but numpy arrays seem more useful
    treeData['Mergers']=np.array(treeData['Mergers'])
    return treeData
    
#returns relevant details for a particular snapshot
def getSnapData(snapshot=135,simulation='Illustris-1'):
    snapUrl='http://www.illustris-project.org/api/'+simulation+'/snapshots/'+str(snapshot)+'/'
    snapData=get(snapUrl)
    data={'Simulation':simulation}
    data['SnapshotNumber']=snapshot
    #could add time
    data['Redshift']=snapData['redshift']
    data['NumPartGas']=snapData['num_gas']
    data['NumPartDM']=snapData['num_dm']
    data['NumPartTracer']=snapData['num_trmc']
    data['NumPartStar']=snapData['num_stars']
    data['NumPartBH']=snapData['num_bhs']
    data['NumHalos']=snapData['num_groups_fof']
    data['NumSubhalos']=snapData['num_groups_subfind']
    return data
 
#returns relevant details for a particular simulation
def getSimData(simulation='Illustris-1',getRedshifts=1):
    simUrl='http://www.illustris-project.org/api/'+simulation+'/'
    simData=get(simUrl)
    #could add table of snapshots, redshifts and times
    data={'Simulation':simulation}
    data['BoxSize']=simData['boxsize']
    h=simData['hubble']
    data['h']=simData['hubble']
    data['Omega_0']=simData['omega_0']
    data['Omega_L']=simData['omega_L']
    data['Omega_B']=simData['omega_B']
    data['MassDM']=simData['mass_dm']
    data['MassGas']=simData['mass_gas']
    
    if getRedshifts==1: # get a list of the redshifts, cosmic time and scale factor of each snapshots
        from scipy import integrate #needed for numerical inetgration to get t(z)
        H0=100*data['h']
        omM=data['Omega_0']+data['Omega_B']
        omL=data['Omega_L']
        def tInt(a):
            return 1/(H0*a*np.sqrt(omL + omM*a**-3))
        
        nSnapshots=simData['num_snapshots']
        snapshotsUrl=simUrl+'snapshots/'
        snapshotsData=get(snapshotsUrl)
        finalSnapshot=snapshotsData[-1]['number'] # may be larger than nSnapshots if there are corrupted files
        snapshots=-np.ones((finalSnapshot+1,4)) #corrupted snapshots will have -1's in redshift, scale factor and time
        snapshots[:,0]=np.arange(0,finalSnapshot+1)
        for i in range(nSnapshots):
            thisSnap=snapshotsData[i]['number'] #note, sometimes a sim may skip a snapshot
            z=snapshotsData[i]['redshift']
            snapshots[thisSnap,1]=z
            a=1/(1+z)
            snapshots[thisSnap,2]=a
            snapshots[thisSnap,3]=integrate.quad(tInt,0,a)[0] #NOT THE SAME AS ON THE ILLUSTRIS WEBSITE (no idea why not tho...)
        data['Redshifts']=snapshots
    return data

#tells the unit conversion routine which units we want
def setUnits(unitScheme):
    changeUnits.setUnits(unitScheme)
    