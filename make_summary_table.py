#!/usr/bin/env python

#  -is it really a potential problem if velocity reference system is not 'lsr'?
#  -why is center sky frequency as calculated with p2gTable.py different than
#   the value in the OT GUI?
#  -check that all frequencies are different and if there are duplicates then
#   issue a message or something
#  -I'm thinking the table should report the number of basebands (not always
#   4) and then where it has BB_1: width... it should instead have something
#   more like:
#      BB_1:
#        SW-1: width: 1875.000MHz, 3840 channels
#      BB_2:
#        SW-1: width: 1875.000MHz, 3840 channels
#        SW-2: width: 1875.000MHz, 3840 channels
#        SW-3: width: 1875.000MHz, 3840 channels ...

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
    Dec = float(Dec)
    (dfrac, dw) = math.modf(Dec)
    d = int(dw)
    tmp = dfrac*60.0
    (arcmfrac, arcm) = math.modf(tmp)
    arcm = int(abs(arcm))
    arcs = (abs(arcmfrac*60.0))

    return ('%02d:%02d:%05.2f'%(h, m, s), '%+03d:%02d:%05.2f'%(d, arcm, arcs))

def restFreq2sky(restFreq, sourceVel, doppType):
    #Kindly copied from p2gTable.py
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
    if aotPath == 'Q': break
    if not os.path.isfile(aotPath):
        print 'Could not access file, try again'
        continue
    else:
        done = True

if aotPath != 'Q':
    #unzip XML files from aot in temporary directory
    shutil.rmtree('nates_temp_dir', ignore_errors=True)
    os.mkdir('nates_temp_dir')
    tmpDir = os.getcwd() + '/nates_temp_dir'
    os.system('unzip -q ' + aotPath + ' -d ' + tmpDir)
    sbXMLFiles = glob.glob(tmpDir + '/SchedBlock*.xml')

    tableInfo = dict()

    #retrieve the project code from ObsProject.xml
    tree = ET.parse(tmpDir + '/ObsProject.xml')
    root = tree.getroot()
    for child in root:
        if 'code' in child.tag:
            tableInfo['Project Code'] = child.text

    tableInfo['Ordered SBs'] = list()
    for sb in sbXMLFiles:
        #read XML document into memory
        tree = ET.parse(sb)
        root = tree.getroot()

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
        dopplerCalcType = list()
        centerVelocity = list()
        for child in root:
            if child.tag == favNS + '}FieldSource':
                for gChild in child:
                    if (gChild.tag == favNS + '}sourceName' and
                        gChild.text != 'query'):
                        name = child.findall(favNS + \
                                             '}name')[0].text
                        if name != 'Primary:': continue
                        #retrieve source name
                        tableInfo[sbName]['Sources'][gChild.text] = dict()
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
                                  lngElem.attrib['unit'] + " or " +\
                                  latElem.attrib['unit'] + \
                                  " as a unit for the " + \
                                  "source coordinates. Look for RA=XXX " + \
                                  "Dec=XXX in the output table to tell " + \
                                  "which source(s) need attention."
                            tableInfo[sbName]['Sources'][gChild.text]['RA'] = \
                                'XXX'
                            tableInfo[sbName]['Sources'][gChild.text]['Dec'] = \
                                'XXX'
                        #grab doppler calculation type and center velocity for
                        #computing the center sky frequencies
                        velElem = child.findall(favNS + '}sourceVelocity')[0]
                        if velElem.attrib['referenceSystem'] != 'lsr':
                            print 'WARNING: ' + \
                                'Vel ref system is ' + \
                                velElem.attrib['referenceSystem'] + '. ' + \
                                'Velocity reference system is not "lsr" ' + \
                                'so this script might not get the ' + \
                                'frequencies right. Make sure you ' + \
                                'carefully check the frequencies.'
                        dopplerCalcType.append(velElem.attrib['dopplerCalcType'])
                        centVelElem = velElem.findall('{' + \
                                                      namespaces['val'] + \
                                                      '}centerVelocity')[0]
                        centerVelocity.append(float(centVelElem.text))
                        if centVelElem.attrib['unit'] == 'm/s':
                            centerVelocity[-1] = centerVelocity/1000.0

        #retrieve the spectral spec
        tableInfo[sbName]['Sky Freqs'] = list()
        for child in root:
            if child.tag == favNS + '}SpectralSpec':
                for gChild in child:
                    if (gChild.tag == favNS + '}name' and 'Science setup' in gChild.text):
                        #retrieve the band
                        freqSet = child.findall(favNS + '}FrequencySetup')[0]
                        tableInfo[sbName]['Band'] = \
                            freqSet.attrib['receiverBand'].split('_')[-1]

                        #retrieve baseband widths and numbers of channels
                        #looks like these initializations may be outdated
                        #compared to the BB_ dictionary below
                        tableInfo[sbName]['Bandwidths'] = list()
                        tableInfo[sbName]['restFrequency'] = list() #added
                        tableInfo[sbName]['avgFactor'] = list()
                        tableInfo[sbName]['N Channels'] = list()
                        tableInfo[sbName]['Division Mode'] = list()
                        #check which correlator we're talking about here...
                        corrPrefx = 'BL'
                        if len(child.findall(favNS + '}' + corrPrefx + 'CorrelatorConfiguration')) == 0:
                            corrPrefx = 'ACA'
                        corrConfig = child.findall(favNS + '}' + corrPrefx + 'CorrelatorConfiguration')[0] #BLCorrelatorConfiguration
                        index = 1
                        for BB in corrConfig.findall(favNS + '}' + corrPrefx + 'BaseBandConfig'):
                            tableInfo[sbName]['BB_' + str(index)] = \
                                {'Bandwidth': list(), 'restFrequency': list(), \
                                 'avgFactor': list(), 'N Channels': list(), \
                                 'Division Mode': list()}
#                            spwElem = BB.findall(favNS + '}' + corrPrefx + 'SpectralWindow')
                            spwElem = BB.findall(favNS + '}' + corrPrefx + 'SpectralWindow')
                            for i in range(len(spwElem)):
#effectiveBandwidth
                                bwElem = spwElem[i].findall(favNS + '}effectiveBandwidth')[0]
                                effBW = bwElem.text
                                unit = bwElem.attrib['unit']
                                if unit == 'GHz':
                                    effBW = float(effBW)*1.0e3
                                elif unit == 'MHz':
                                    effBW = float(effBW)
                                else:
                                    effBW = -9999.9999
                                    print "I don't know how to handle " + \
                                          unit + " as a unit for the " + \
                                          "effective bandwidth. Look for " + \
                                          "a bandwidth of -999.999 in the " + \
                                          "output table to tell which " + \
                                          "baseband(s) need attention."
                                effBW = '%4.3f'%effBW
                                tableInfo[sbName]['BB_' + str(index)]['Bandwidth'].append(effBW)
#effectiveNumberOfChannels
                                effNChan = spwElem[i].findall(favNS + '}effectiveNumberOfChannels')[0].text
                                #TDM or FDM?
                                if effNChan == '128' or effNChan == '124':
                                    tableInfo[sbName]['BB_' + str(index)]['Division Mode'].append('TDM')
                                else:
                                    tableInfo[sbName]['BB_' + str(index)]['Division Mode'].append('FDM')
                                tableInfo[sbName]['BB_' + str(index)]['N Channels'].append(effNChan)
#spectralAveragingFactor
                                avgFact = spwElem[i].findall(favNS + '}spectralAveragingFactor')[0].text
                                tableInfo[sbName]['BB_' + str(index)]['avgFactor'].append(avgFact)

#restFrequency 
                                rFreq = spwElem[i].findall(favNS + '}SpectralLine')
                                for BB in rFreq:
                                    rfElem = rFreq[0].findall(favNS + '}restFrequency')[0]
                                    effRF = rfElem.text
                                    effRF = float(effRF)
                                    effRF = '%7.3f'%effRF
                                    tableInfo[sbName]['BB_' + str(index)]['restFrequency'].append(effRF)

                            index += 1

                        #grab the center rest frequency and compute the center
                        #sky frequency
                        for BB in freqSet.findall(favNS + '}BaseBandSpecification'):
                            centFreqElem = BB.findall(favNS + '}centerFrequency')[0]
                            centFreq = float(centFreqElem.text)
                            centFreqU = centFreqElem.attrib['unit']
                            if centFreqU == 'Hz':
                                centFreq /= 1.0e9
                            elif centFreqU == 'kHz':
                                centFreq /= 1.0e6
                            elif centFreqU == 'MHz':
                                centFreq /= 1.0e3
#                            #do Doppler correction when Doppler Reference is rest
#                            if freqSet.attrib['dopplerReference'] == 'rest':
                            tmp = restFreq2sky(centFreq, \
                                               centerVelocity[0], \
                                               dopplerCalcType[0])
 #                           else:
 #                               tmp = centFreq
                            tableInfo[sbName]['Sky Freqs'].append(str(round(tmp, 1)))

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
                    intTime*len(tableInfo[sbName]['Sources'])
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
    print 'Scheduling Block Info for ' + tableInfo['Project Code']
    if len(tableInfo['Ordered SBs']) > 1:
        tmp = str(tableInfo['Ordered SBs'])
        tmp = tmp.replace('[', '')
        tmp = tmp.replace(']', '')
        tmp = tmp.replace("'", "")
        print 'Includes SBs: '  + tmp
    print ''
    for sbName in tableInfo['Ordered SBs']:
        print 'SB name: ' + sbName#tableInfo[sbName]['SB Name']
	if (sbName.find("TE") > 1) and (sbName.find("TC") > 1):
        	print 'Array and Correlator: 12m Compact and Extended, Baseline Correlator'
	elif ((sbName.find("TE") > 1) and (sbName.find("TC") < 1)) or ((sbName.find("TE") < 1) and (sbName.find("TC") > 1)):
        	print 'Array and Correlator: 12m, Baseline Correlator'
	else:
       		print 'Array and Correlator: 7m, ACA Correlator'

        if len(tableInfo[sbName]['Sources']) > 1:
            print 'Sources:'
            for source in sorted(tableInfo[sbName]['Sources']):
                print source + ', RA=' + \
                      tableInfo[sbName]['Sources'][source]['RA'] + \
                      ' Dec=' + tableInfo[sbName]['Sources'][source]['Dec']
        else:
            tmp = tableInfo[sbName]['Sources'].keys()[0]
            print 'Source: ' + tmp
            print 'Position: RA=' +  tableInfo[sbName]['Sources'][tmp]['RA'] + \
                  ' Dec=' + tableInfo[sbName]['Sources'][tmp]['Dec']
        tmp = str(len(tableInfo[sbName]['Sky Freqs']))
        tmp2 = 'Band ' + tableInfo[sbName]['Band'] + ': ' + tmp + \
               ' Basebands Centered at Sky Frequency '
        for i in range(int(tmp)):
            tmp2 += tableInfo[sbName]['Sky Freqs'][i] + '/'
        tmp2 = tmp2[:-1] + ' GHz'
        print tmp2
        tmp2 = 'Correlator modes for ' + tmp + ' Basebands: '
        # Get all the BB keys for the dictionary, and sort them
        bb_keys = [bb_key for bb_key in tableInfo[sbName].keys() if 'BB_' in bb_key]
        bb_keys.sort()
        # Print the observing mode for each BB
        for bb_key in bb_keys:
            tmp2 += tableInfo[sbName][bb_key]['Division Mode'][0] + '/'
        tmp2 = tmp2[:-1]
        print tmp2
        spwNum = 0  #only used when each BB in SB contains only 1 SPW
        for i in range(1, int(tmp)+1, 1):
            if len(tableInfo[sbName]['BB_' + str(i)]['Bandwidth']) != 1:
                print 'BB' + str(i) + ':'
                nSpaces = 2
#                spwNum = ''
                noBB = False
            else:
                nSpaces = 0
#                spwNum = str(spwNum + 1)
                spwNum += 1
                noBB = True
#this assumes n channels divided by averaging factor is an integer and I'm not perfectly confident that's a guarenteed assumption
            for j in range(len(tableInfo[sbName]['BB_' + str(i)]['Bandwidth'])):
                if noBB:
                    spwNumStr = str(spwNum)
                else:
                    spwNumStr = str(j+1)
                print ' '*nSpaces + 'SPW' + spwNumStr + ': rest freq: ' + \
                "%.2f" % float(tableInfo[sbName]['BB_' + str(i)]['restFrequency'][j]) + ' GHz, ' + \
                'effective bandwidth: ' + tableInfo[sbName]['BB_' + str(i)]['Bandwidth'][j] + ' MHz, ' + \
                str(int(tableInfo[sbName]['BB_' + str(i)]['N Channels'][j])/int(tableInfo[sbName]['BB_' + str(i)]['avgFactor'][j])) + \
                ' channels'
        print tableInfo[sbName]['T per Exec'] + \
              ' mins on source per execution, ' + \
              tableInfo[sbName]['T on Source'] + ' mins on source total'
        print ''

    #remove my temporary directory
    os.system('rm -rf ' + tmpDir)
