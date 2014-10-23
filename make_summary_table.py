#!/usr/bin/env python

import os, sys, shutil
import glob
import math
import xml.etree.ElementTree as ET
from cStringIO import StringIO

def dec2sexa(RA, Dec):
    #convert RA from decimal degree to sexagesimal
    RA = float(RA)
    (hfrac, hw) = math.modf(RA)
    h = int(hw)/15
    tmp = RA - (h*15.0)
    tmp *= 4.0
    (mfrac, m) = math.modf(tmp)
    m = int(m)
    s = mfrac*60.0

    #convert Dec
    sign = math.copysign(1, float(Dec))
    spltDec = Dec.split('.')
    d = int(spltDec[0])                 #I do these string acrobatics to avoid
    tmp = float('0.' + spltDec[1])*60.0 #inherent roundoff error in floats
    tmp = str(tmp)
    spltTmp = tmp.split('.')
    arcm = abs(int(spltTmp[0]))
    arcs = abs(float('0.' + spltTmp[1])*60.0)
#    Dec = float(Dec)
#    sign = math.copysign(1, Dec)
#    (dfrac, dw) = math.modf(Dec)
#    d = int(dw)
#    tmp = dfrac*60.0
#    (arcmfrac, arcm) = math.modf(tmp)
#    arcm = int(abs(arcm))
#    arcs = (abs(arcmfrac*60.0))

    #if d is 0 then negative sign of declination has to be added manually
    if d == 0 and sign == -1.0:
        return ('%02d:%02d:%05.2f'%(h, m, s), '-%02d:%02d:%05.2f'%(d, arcm, \
                                                                   arcs))
    else:
        return ('%02d:%02d:%05.2f'%(h, m, s), '%+03d:%02d:%05.2f'%(d, arcm, \
                                                                   arcs))

#not actually used, kept around just in case...
def restFreq2sky(restFreq, sourceVel, doppType):
    #kindly copied from p2gTable2.py
    #restFreq in GHz, sourceVel in km/s
    c = 299792.458 #km/s
    skyFreq = 0.0
    if doppType == 'RELATIVISTIC':
        skyFreq = restFreq*((1 - (sourceVel/c)**2)**0.5)/(1 + (sourceVel/c))
    elif doppType == "RADIO":
        skyFreq = float(restFreq*(1 - (sourceVel/c)))
    elif doppType == "OPTICAL":
        skyFreq = float(restFreq*((1 + (sourceVel/c))**-1))
    return skyFreq

#ask for path to aot file
firstTime = True
done = False
while not done:
    if firstTime:
        if len(sys.argv) > 1: 
            aotPath = sys.argv[1]
        else:
            aotPath = raw_input('Enter path to aot file ("Q" to quit)\n==>')
        firstTime = False
    else:
        aotPath = raw_input('==>')
    if aotPath == 'Q': sys.exit('Quitting...')
    if not os.path.isfile(aotPath):
        print 'Could not access file, try again.'
        continue
    else:
        done = True

#unzip XML files from aot in temporary directory
shutil.rmtree('nates_temp_dir', ignore_errors=True)
os.mkdir('nates_temp_dir')
tmpDir = os.getcwd() + '/nates_temp_dir'
os.system('unzip -q ' + aotPath + ' -d ' + tmpDir)
sbXMLFiles = glob.glob(tmpDir + '/SchedBlock*.xml')

#initialize dictionary for all necessary table info
tableInfo = dict()

#retrieve the project code from ObsProject.xml
tree = ET.parse(tmpDir + '/ObsProject.xml')
root = tree.getroot()
for child in root:
    if 'code' in child.tag:
        tableInfo['Project Code'] = child.text

#sort sbXMLFiles so table has same order as in AOT
tmp = dict()
for sb in sbXMLFiles:
    num = sb.split('SchedBlock')[1].split('.')[0]
    tmp[num] = sb
sbXMLFiles = list()
indices = tmp.keys()
indices.sort(key=int)
for ind in indices:
    sbXMLFiles.append(tmp[ind])

#loop over each SchedBlock#.xml files retrieving the necessary info
tableInfo['Ordered SBs'] = list()
for sb in sbXMLFiles:
    #read XML document into memory
    tree = ET.parse(sb)
    root = tree.getroot()

    ####
    #do some ugly stuff so I can access the prefixes
    #courtesy of:
    #   http://blog.tomhennigan.co.uk/post/46945128556/elementtree-and-xmlns
    with open(sb, 'r') as f:
        xmlin = f.read()
    xml = None
    namespaces = {}
    for event, elem in ET.iterparse(StringIO(xmlin), ('start', 'start-ns')):
        if event == 'start-ns':
            if elem[0] in namespaces and namespaces[elem[0]] != elem[1]:
                raise KeyError("Duplicate prefix with different URI found.")
            namespaces[str(elem[0])] = elem[1]
        elif event == 'start':
            if xml is None:
                xml = elem
                break
    for prefix, uri in namespaces.iteritems():
        ET.register_namespace(prefix, uri)
    ####

    #stick {sbl: into a variable since we use it so much
    favNS = '{' + namespaces['sbl']

    #retrieve the SB name
    for child in root:
        if child.tag == '{' + namespaces['prj'] + '}name':
            tableInfo[child.text] = dict()
            sbName = child.text
            tableInfo['Ordered SBs'].append(sbName)
            break

    #retrieve the info on the individual source(s)
    tableInfo[sbName]['Sources'] = dict()
    tableInfo[sbName]['Sources']['Ordered Sources'] = list()
    for child in root:
        if child.tag == favNS + '}FieldSource':
            for gChild in child:
                if (gChild.tag == favNS + '}sourceName' and
                    gChild.text != 'query'):
                    #retrieve source name
                    tableInfo[sbName]['Sources'][gChild.text] = dict()
                    tableInfo[sbName]['Sources']['Ordered Sources'].append(gChild.text)
                    #retrieve source coordinates
                    coordElem = \
                        child.findall(favNS + '}sourceCoordinates')[0]
                    lngElem = coordElem.findall('{' + namespaces['val'] + \
                                                '}longitude')[0]
                    lngDeg = lngElem.text
                    latElem = coordElem.findall('{' + namespaces['val'] + \
                                                '}latitude')[0]
                    latDeg = latElem.text
                    if (lngElem.attrib['unit'] == 'deg' and \
                        latElem.attrib['unit'] == 'deg'):
                        tableInfo[sbName]['Sources'][gChild.text]['RA'], \
                        tableInfo[sbName]['Sources'][gChild.text]['Dec'] = \
                            dec2sexa(lngDeg, latDeg)
                    else:
                        print "I don't know how to handle " + \
                              lngElem.attrib['unit'] + " or " + \
                              latElem.attrib['unit'] + " as a unit for the " + \
                              "source coordinates. Look for RA=XXX Dec=XXX " + \
                              "in the output table to tell which source(s) " + \
                              "need attention."
                        tableInfo[sbName]['Sources'][gChild.text]['RA'] = 'XXX'
                        tableInfo[sbName]['Sources'][gChild.text]['Dec'] = 'XXX'

    #retrieve the SpectralSpec element for the Science setup
    gotIt = False
    for child in root:
        if child.tag == favNS + '}SpectralSpec':
            for gChild in child:
                if gChild.tag == favNS + '}name' and \
                   'Science setup' in gChild.text:
                    gotIt = True
                    break
            if gotIt:
                break

    #retrieve the band
    freqSet = child.findall(favNS + '}FrequencySetup')[0]
    tableInfo[sbName]['Band'] = freqSet.attrib['receiverBand'].split('_')[-1]

    #retrieve BaseBandSpecification center frequencies and part IDs
    entityIDs = list()
    bbSpecFreqs = list()
    for BB in freqSet.findall(favNS + '}BaseBandSpecification'):
        entityIDs.append(BB.attrib['entityPartId'])
        bbSpecFreqs.append(BB.findall(favNS + '}centerFrequency')[0].text)
        if BB.findall(favNS + '}centerFrequency')[0].attrib['unit'] == 'MHz':
            bbSpecFreqs[-1] = float(bbSpecFreqs[-1])/1e3
        elif BB.findall(favNS + '}centerFrequency')[0].attrib['unit'] == 'GHz':
            bbSpecFreqs[-1] = float(bbSpecFreqs[-1])
        else:
            print "I don't know how to handle " + \
                  BB.findall(favNS + '}centerFrequency')[0].attrib['unit'] + \
                  " as a unit for the SPW center frequency. Look for a " + \
                  "center frequency that is really negative to determine " + \
                  "which baseband(s) need attention."
            bbSpecFreqs[-1] = float(-1e25)

    #retrieve appropriate CorrelatorConfiguration (BL or ACA)
    corrPrefx = 'BL'
    if len(child.findall(favNS + '}' + corrPrefx + \
           'CorrelatorConfiguration')) == 0: corrPrefx = 'ACA'
    corrConfig = child.findall(favNS + '}' + corrPrefx + \
                               'CorrelatorConfiguration')[0]
    tableInfo[sbName]['N Basebands'] = \
        len(corrConfig.findall(favNS + '}' + corrPrefx + 'BaseBandConfig'))

    #retrieve baseband configuration information
    index = 1
    for BB in corrConfig.findall(favNS + '}' + corrPrefx + 'BaseBandConfig'):
        tableInfo[sbName]['BB_' + str(index)] = {'Bandwidth': list(), \
                                                 'restFrequency': list(), \
                                                 'avgFactor': list(), \
                                                 'N Channels': list(), \
                                                 'Division Mode': list()}
        spwElem = BB.findall(favNS + '}' + corrPrefx + 'SpectralWindow')
        polAtt = spwElem[0].attrib['polnProducts']
        if polAtt == 'XX':
            tableInfo[sbName]['Polarization State'] = 'Single'
        elif polAtt == 'XX,YY':
            tableInfo[sbName]['Polarization State'] = 'Dual'
        elif polAtt == 'XX,YY,XY,YX':
            tableInfo[sbName]['Polarization State'] = 'Full'
        else:
            print 'Unrecognized polarization products, this needs a closer look.'

        #retrieve base band partID and sideband
        partID = BB.findall(favNS + \
                            '}BaseBandSpecificationRef')[0].attrib['partId']
        sideBand = spwElem[0].attrib['sideBand']

        freqs = list()
        for i in range(len(spwElem)):
            #retrieve effective bandwidth
            bwElem = spwElem[i].findall(favNS + '}effectiveBandwidth')[0]
            effBW = bwElem.text
            unit = bwElem.attrib['unit']
            if unit == 'GHz':
                effBW = float(effBW)*1.0e3
            elif unit == 'MHz':
                effBW = float(effBW)
            else:
                effBW = -9999.9999
                print "I don't know how to handle " + unit + " as a unit " + \
                      "for the effective bandwidth. Look for a bandwidth " + \
                      "of -999.999 in the output table to tell which " + \
                      "baseband(s) need attention."
            effBW = '%4.3f'%effBW
            tableInfo[sbName]['BB_' + str(index)]['Bandwidth'].append(effBW)

            #retrieve effective number of channels
            effNChan = spwElem[i].findall(favNS + \
                           '}effectiveNumberOfChannels')[0].text

            #TDM or FDM?
            if effNChan == '128' or effNChan == '124':
                tableInfo[sbName]['BB_' + \
                      str(index)]['Division Mode'].append('TDM')
            else:
                tableInfo[sbName]['BB_' + \
                      str(index)]['Division Mode'].append('FDM')
            tableInfo[sbName]['BB_' + \
                      str(index)]['N Channels'].append(effNChan)

            #retrieve channel averaging factor
            avgFact = spwElem[i].findall(favNS + \
                             '}spectralAveragingFactor')[0].text
            tableInfo[sbName]['BB_' + \
                        str(index)]['avgFactor'].append(avgFact)

            #retrieve the SPW offset
            centElem = spwElem[i].findall(favNS + '}centerFrequency')[0]
            freqs.append(centElem.text)
            if centElem.attrib['unit'] == 'MHz':
                freqs[-1] = float(freqs[-1])/1e3
            elif centElem.attrib['unit'] == 'GHz':
                freqs[-1] = float(freqs[-1])
            else:
                print "I don't know how to handle " + \
                      centElem.attrib['unit'] + " as a unit " + \
                      "for the SPW center frequency. Look for a center " + \
                      "frequency that is really negative to determine which" + \
                      "baseband(s) need attention."
                freqs[-1] = float(-1e25)

            #retrieve the approximate SPW rest frequency
#            rFreq = spwElem[i].findall(favNS + '}SpectralLine')
#            rfElem = rFreq[0].findall(favNS + '}restFrequency')[0]
#            effRF = rfElem.text
#            effRF = float(effRF)
#            effRF = '%7.3f'%effRF
#            tableInfo[sbName]['BB_' + str(index)]['restFrequency'].append(effRF)

        #calculate SPW center frequencies
        for i in range(len(entityIDs)):
            if entityIDs[i] == partID:
               ind = i
               break
        for i in range(len(freqs)):
            if sideBand == 'USB':
                if freqs[i] > 3.0:
                    junkie = bbSpecFreqs[ind] + abs(freqs[i] - 3.0)
                else:
                    junkie = bbSpecFreqs[ind] - abs(freqs[i] - 3.0)
            else:
                if freqs[i] > 3.0:
                    junkie = bbSpecFreqs[ind] - abs(freqs[i] - 3.0)
                else:
                    junkie = bbSpecFreqs[ind] + abs(freqs[i] - 3.0)
            print junkie
            tableInfo[sbName]['BB_' + str(index)]['restFrequency'].append('%7.3f'%junkie)
        index += 1

    #retrieve the time on source per execution and total time on source
    for child in root:
        if child.tag == favNS + '}ScienceParameters':
            intElem = child.findall(favNS + '}integrationTime')[0]
            intUnit = intElem.attrib['unit']
            intTime = float(intElem.text)
            if intUnit == 's':
                intTime /= 60.0
            elif intUnit == 'h':
                intTime *= 60.0
            tableInfo[sbName]['T per Exec'] = \
                intTime*len(tableInfo[sbName]['Sources']['Ordered Sources'])
            break
    for child in root:
        if child.tag == favNS + '}SchedBlockControl':
            execCount = child.findall(favNS + '}executionCount')[0].text
            tableInfo[sbName]['T on Source'] = \
                float(execCount)*tableInfo[sbName]['T per Exec']
            tableInfo[sbName]['T on Source'] = \
                str(round(tableInfo[sbName]['T on Source'], 1))
            break
    tableInfo[sbName]['T per Exec'] = \
        str(round(tableInfo[sbName]['T per Exec'], 1))

#print out the info!!!
#print the header information
print 'Scheduling Block Info for ' + tableInfo['Project Code']
if len(tableInfo['Ordered SBs']) > 1:
    tmp = str(tableInfo['Ordered SBs'])
    tmp = tmp.replace('[', '')
    tmp = tmp.replace(']', '')
    tmp = tmp.replace("'", "")
    print 'Includes SBs: '  + tmp
print ''

#do a pre-check to see if SBs are all extended, compact or a mix
mixed = False
check = ''
for sbName in tableInfo['Ordered SBs']:
    if sbName[-2] == 'T':
        check = sbName[-1]
if len(check) > 0:
    for sbName in tableInfo['Ordered SBs']:#modify for finding '7m'
        if sbName[-1] != check and sbName[-1] != 'M':
            mixed = True
#print the correlator information
for sbName in tableInfo['Ordered SBs']:
    print 'SB name: ' + sbName
    if sbName[-2] == 'T':
        if sbName[-1] == 'E':
            print 'Array and Correlator: 12m' + ' extended'*mixed + ', Baseline Correlator'
        elif sbName[-1] == 'C':
            print 'Array and Correlator: 12m' + ' compact'*mixed + ', Baseline Correlator'
        else:
            print 'WARNING: could not determine array and correlator ' + \
                  'from SB name.'
    elif sbName[-2] == '7M':
        print 'Array and Correlator: 7m, ACA Correlator'
    else:
        print 'WARNING: could not determine array and correlator ' + \
              'from SB name.'
                
    if len(tableInfo[sbName]['Sources']) > 2:
        print 'Sources:'
        for source in tableInfo[sbName]['Sources']['Ordered Sources']:
            print '  ' + source + ', RA=' + \
                  tableInfo[sbName]['Sources'][source]['RA'] + \
                  ' Dec=' + tableInfo[sbName]['Sources'][source]['Dec']
    else:
        tmp = tableInfo[sbName]['Sources'].keys()[0]
        if tmp == 'Ordered Sources': tmp = tableInfo[sbName]['Sources'].keys()[1]
        print 'Source: ' + tmp
        print 'Position: RA=' +  tableInfo[sbName]['Sources'][tmp]['RA'] + \
              ' Dec=' + tableInfo[sbName]['Sources'][tmp]['Dec']
    tmp2 = 'Correlator modes for Band ' + tableInfo[sbName]['Band'] + \
           ' basebands: '
    #get all the BB keys for the dictionary, and sort them
    bbKeys = [bbKey for bbKey in tableInfo[sbName].keys() if 'BB_' in bbKey]
    bbKeys.sort()
    #print the correlator mode for each BB
    for bbKey in bbKeys:
        tmp2 += tableInfo[sbName][bbKey]['Division Mode'][0] + '/'
    tmp2 = tmp2[:-1] + ', ' + tableInfo[sbName]['Polarization State'] + ' pol.'
    print tmp2
    #do a pre-check to see if any BB have more than one 1 SPW
    bbFlag = False
    for bbKey in bbKeys:
        if len(tableInfo[sbName][bbKey]['Bandwidth']) != 1:
            bbFlag = True
    spwNum = 0  #only used when each BB in SB contains only 1 SPW
    for bbKey in bbKeys:
        if bbFlag:
            print bbKey + ':'
            nSpaces = 2
            noBB = False
        else:
            nSpaces = 0
            spwNum += 1
            noBB = True
        for j in range(len(tableInfo[sbName][bbKey]['Bandwidth'])):
            if noBB:
                spwNumStr = str(spwNum)
            else:
                spwNumStr = str(j+1)
            print ' '*nSpaces + 'SPW' + spwNumStr + ': rest freq: ' + \
            '%.2f' % float(tableInfo[sbName][bbKey]['restFrequency'][j]) + \
            ' GHz, ' + 'effective bandwidth: ' + \
            tableInfo[sbName][bbKey]['Bandwidth'][j] + ' MHz, ' + \
            str(int(tableInfo[sbName][bbKey]['N Channels'][j])/\
                int(tableInfo[sbName][bbKey]['avgFactor'][j])) + \
            ' channels'
    print tableInfo[sbName]['T per Exec'] + \
          ' mins on source per execution, ' + \
          tableInfo[sbName]['T on Source'] + ' mins on source total'
    print ''

##remove my temporary directory
os.system('rm -rf ' + tmpDir)
