import os
import argparse
from aotInfo2 import *

version = 0.2
#0.01 December 2012
#0.02 April 2014 (Cycle 2)

c = 299792.458
dictBands = {'03': [84.0, 116.0], '04': [125.0, 163.0], '06': [211.0, 275.0], '07': [275.0, 373.0], '08': [385.0, 500.0], '09': [602.0, 720.0]}

def decimaldeg2dms(x, raflag = '') :
	"""
	Converts decimal degrees to Hours:Minutes:Seconds
	If ra is True, then we are converting a Ra measurment
	and we devide by 15 to go from 0-->360deg to 0--->24 hours.
	Else, we are converting a signed Dec measurement

	"""
	if raflag == True:
		x = x/15.
	elif raflag == False:
		x = x
	elif raflag == '':
		print 'You did not specifiy if the dms measurement was RA or Dec. Set ra flag to True or False.'
		return

	if x < 0 :
		sgn = '-'
		x = -x
	else : sgn = ''
	deg = int(x)
	arcmin = int((x-deg)*60.0)
	arcsec  = float((x-deg-arcmin/60.0)*3600.)
	return ('%s%02d:%02d:%05.2F' % (str(sgn),deg,arcmin,arcsec))

def checkExistsSpectralSpec(spectralSpecToCheck, listSpectralSpec):
	spectralSpecExists = True
	listSW = []
	for basebandSpecificationsIndex in spectralSpecToCheck.basebandSpecifications:
		listSW.append(float(spectralSpecToCheck.basebandSpecifications[basebandSpecificationsIndex].centerFrequencyValue))
	if len(listSpectralSpec) > 0:
		for spectralSpec in listSpectralSpec:
			for basebandSpecificationsIndex in spectralSpec.basebandSpecifications:	
				temp = False
				for SWNode in listSW:
					if SWNode == spectralSpec.basebandSpecifications[basebandSpecificationsIndex].centerFrequencyValue:
						temp = True
				spectralSpecExists = spectralSpecExists and temp
		return spectralSpecExists
	else:
		return False

def printInfo(fileAOT, fileOutput):
	try:
		AOT = aotInfo(fileAOT)
		project = AOT.getProject()
		proposal = AOT.getProposal()

		print 'Project code: %s' % project.code
		print 'PI name: %s' % project.pi
		print 'Project title: %s' % project.name
		print 'P2G Phase II originator: P2_originator'
		print 'Supporting ARC: %s' % proposal.obsProposalFeedBack.ARC
		print 'P2G Phase II contact: P2_contact'
		print 'ARC contact scientist(s): CS_name'
		print 'Modifications mandated by the Proposal Review Process (if any): None'
		print 'Special note (if any): None'
		print 'Version: %s\n' % project.version
		print '||  *SB name*  ||  *Source Name*  ||  *RA*  ||  *Dec*  ||  *Ref.Freq. (GHz)*  ||  *Rep.BW (MHz)*  ||  *Band*  ||  *Frqs. (GHz)*  ||  *Min.Ang.Res (arcsec)*  ||  *Max.Ang.Res (arcsec)*  ||  *Array type*  ||  *No.Exec.*  ||  *ToS (min)*  ||  *Pointings*  ||  *Sources*  ||  *ToS per Exec. (min)*  ||  *Total ToS (min)*  ||  *Note(s)*  ||'

		if fileOutput != None:
			fileOutput.write('Project code: %s (version: %s)\n' % (project.code, project.version))
			fileOutput.write('PI name: %s\n' % project.pi)
			fileOutput.write('Project title: %s\n' % project.name)
			fileOutput.write('P2G Phase II originator: P2_originator\n')
			fileOutput.write('Supporting ARC: %s\n' % proposal.obsProposalFeedBack.ARC)
			fileOutput.write('P2G Phase II contact: P2_contact\n')
			fileOutput.write('ARC contact scientist(s): CS_name\n')
			fileOutput.write('Modifications mandated by the Proposal Review Process (if any): None\n')
			fileOutput.write('Special note (if any): None\n')
			fileOutput.write('Version: %s\n\n' % project.version)
			fileOutput.write('||  *SB name*  ||  *Source Name*  ||  *RA*  ||  *Dec*  ||  *Ref.Freq. (GHz)*  ||  *Rep.BW (MHz)*  ||  *Band*  ||  *Frqs. (GHz)*  ||  *Min.Ang.Res (arcsec)*  ||  *Max.Ang.Res (arcsec)*  ||  *Array type*  ||  *No.Exec.*  ||  *ToS (min)*  ||  *Pointings*  ||  *Sources*  ||  *ToS per Exec. (min)*  ||  *Total ToS (min)*  ||  *Note(s)*  ||\n')

		scienceGoals = project.getScienceGoalsList()
		warnings = ''
		dictSB = {}
		for scienceGoalIndex in scienceGoals:
			scienceGoal = scienceGoals[scienceGoalIndex]
			if scienceGoal.obsUnitSets != None:
				if scienceGoal.targetParameter.system != 'J2000':
					warnings += ('WARNING: Science Goal: %s is in %s coordinates\n' % (scienceGoal.name, scienceGoal.targetParameter.system))
				for schedBlockIndex in scienceGoal.obsUnitSets.schedBlocks:
					isAmpCal = False
					schedBlock = scienceGoal.obsUnitSets.schedBlocks[schedBlockIndex]
					if schedBlock.name in dictSB:
						dictSB[schedBlock.name] += 1
					else:
						dictSB[schedBlock.name] = 1
					points = scienceGoal.targetParameter.totalPoints
					executionCount = schedBlock.executionCount
					if schedBlock.obsSchedBlockConstraints.system != 'J2000':
						warnings += ('WARNING: SchedBlock: %s is in %s coordinates\n' % (schedBlock.name, schedBlock.obsSchedBlockConstraints.system))
					representativeFrequencyValue = schedBlock.representativeFrequencyValue
					representativeBandwidthValue = schedBlock.representativeBandwidthValue
					representativeLongitudeValue = decimaldeg2dms(schedBlock.obsSchedBlockConstraints.longitudeValue, raflag = True)
					representativeLatitudeValue = decimaldeg2dms(schedBlock.obsSchedBlockConstraints.latitudeValue, raflag = False)
					counter = 0
					listSpectralSpec = []
					listTargets = {}
					for observingGroupIndex in schedBlock.observingGroup:
						observingGroup = schedBlock.observingGroup[observingGroupIndex]
						if counter > 0:
							for targetIndex in observingGroup.obsOrdTargets:
								target = observingGroup.obsOrdTargets[targetIndex].obsTarget
								if target.obsParameter.typeParameter == 'Science' or target.obsParameter.typeParameter == 'AmpCal':
									if target.obsParameter.typeParameter == 'AmpCal':
										isAmpCal = True
									else:
										listTargets[target.obsFieldSource.name] = [decimaldeg2dms(target.obsFieldSource.longitudeValue, raflag = True), decimaldeg2dms(target.obsFieldSource.latitudeValue, raflag = False), target.obsFieldSource.totalPoints, target.obsFieldSource.name, target.obsFieldSource.system]
									representativeLongitudeValue = decimaldeg2dms(target.obsFieldSource.longitudeValue, raflag = True)
									representativeLatitudeValue = decimaldeg2dms(target.obsFieldSource.latitudeValue, raflag = False)
									if checkExistsSpectralSpec(target.obsSpectralSpec, listSpectralSpec) == False:
										listSpectralSpec.append(target.obsSpectralSpec)
						counter += 1
					SW = ''
					representativeTarget = None
					if len(listSpectralSpec) > 0:
						scienceGoal.performance.configurations = ''
						totalPower = 'N'
						# if representativeFrequencyValue > 0:
						# 	LARS = 0.
						# 	AR = 0.
						# 	ACA = 'N'
						# 	if schedBlock.obsSchedBlockConstraints.calcLASValue > 0:
						# 		AR = schedBlock.obsSchedBlockConstraints.calcARValue
						# 		LAS = schedBlock.obsSchedBlockConstraints.calcLASValue
						# 		ACA = 'N'
						# 	else:
						# 		AR = scienceGoal.performance.desiredAngularResolutionValue
						# 		LAS = scienceGoal.performance.desiredLargestScaleValue
						# 		ACA = scienceGoal.performance.useACA
						# 	arrayConfiguration = getArrayConfiguration(AR, LAS, representativeFrequencyValue, float(scienceGoal.targetParameter.latitudeValue), ACA)
						# 	scienceGoal.performance.configurations = arrayConfiguration[:-2]
						# 	scienceGoal.performance.totalPower = arrayConfiguration[-1:]
						# 	totalPower = scienceGoal.performance.totalPower, scienceGoal.performance.totalPower
						# else:
						# 	if representativeFrequencyValue == 0:
						# 		representativeFrequencyValue = schedBlock.obsSchedBlockConstraints.representativeFrequencyValue
						# 	representativeBandwidthValue = lastRepresentativeBandwidthValue 
						# 	scienceGoal.performance.configurations = lastConfiguration
						# 	schedBlock.integrationTimeValue = lastIntergrationTime
						if schedBlock.arrayType != 'TWELVE-M':
							scienceGoal.performance.configurations = ''
						SW = ''
						for spectralSpec in listSpectralSpec:
							band = spectralSpec.receiverBand
							for basebandSpecificationsIndex in sorted(spectralSpec.basebandSpecifications, key=spectralSpec.basebandSpecifications.get): #spectralSpec.basebandSpecifications:	
								skyFrequency = spectralSpec.basebandSpecifications[basebandSpecificationsIndex].skyFrequencyValue #+ ((spectralSpec.basebandSpecifications[basebandSpecificationsIndex].centerOffsetFrequencyValue - 3) * spectralSpec.basebandSpecifications[basebandSpecificationsIndex].centerOffsetFrequencySign)
								SW = SW + str(round(skyFrequency, 1)) + '/'
								center = spectralSpec.basebandSpecifications[basebandSpecificationsIndex].skyFrequencyPureValue
								if args.verbose == True:
									print '%.1f - (35 * %.3f / c): %.3f < Sky Freq: %.3f = %s' % (dictBands[band.replace('ALMA_RB_', '')][1] - 1, center, ((dictBands[band.replace('ALMA_RB_', '')][1] - 1) - (35 * center / c)), center, (dictBands[band.replace('ALMA_RB_', '')][1] - 1) - (35 * center / c) < center)
									print '%.1f + (35 * %.3f / c): %.3f > Sky Freq: %.3f = %s' % (dictBands[band.replace('ALMA_RB_', '')][0] + 1, center, ((dictBands[band.replace('ALMA_RB_', '')][0] + 1) + (35 * center / c)), center, (dictBands[band.replace('ALMA_RB_', '')][0] + 1) + (35 * center / c) > center)
									if fileOutput != None:
										fileOutput.write('%.1f - (35 * %.3f / c): %.3f < Sky Freq: %.3f = %s\n' % (dictBands[band.replace('ALMA_RB_', '')][1] - 1, center, ((dictBands[band.replace('ALMA_RB_', '')][1] - 1) - (35 * center / c)), center, (dictBands[band.replace('ALMA_RB_', '')][1] - 1) - (35 * center / c) < center))
										fileOutput.write('%.1f + (35 * %.3f / c): %.3f > Sky Freq: %.3f = %s\n' % (dictBands[band.replace('ALMA_RB_', '')][0] + 1, center, ((dictBands[band.replace('ALMA_RB_', '')][0] + 1) + (35 * center / c)), center, (dictBands[band.replace('ALMA_RB_', '')][0] + 1) + (35 * center / c) > center))
								if center > ((dictBands[band.replace('ALMA_RB_', '')][1] - 1) - (35 * center / c)):
									warnings += 'WARNING: SB %s is too close to the upper B%d band edge.  Please decrease %s center frq to at least: %.3f\n' % (schedBlock.name, int(band.replace('ALMA_RB_', '')), spectralSpec.basebandSpecifications[basebandSpecificationsIndex].name, ((dictBands[band.replace('ALMA_RB_', '')][1] - 1) - (35 * center / c)))
								if center < ((dictBands[band.replace('ALMA_RB_', '')][0] + 1) + (35 * center / c)):
									warnings += 'WARNING: SB %s is too close to the lower B%d band edge.  Please increase %s center frq to at least: %.3f\n' % (schedBlock.name, int(band.replace('ALMA_RB_', '')), spectralSpec.basebandSpecifications[basebandSpecificationsIndex].name, ((dictBands[band.replace('ALMA_RB_', '')][0] + 1) + (35 * center / c)))
						SW = SW[:-1]
						if isAmpCal == True:
							note = 'Calibration SB'
						else:
							note = 'None'
						for targetIndex in listTargets:
							if listTargets[targetIndex][0] == representativeLongitudeValue and listTargets[targetIndex][1] == representativeLatitudeValue:
								representativeTarget = listTargets[targetIndex]
						if representativeTarget == None:
							representativeTarget = [0, 0, 0, '']
						print '| *%s*  | %s  | %s  | %s  | %5.1f  | %.1f  | %s | %s  | %.2f | %.2f | %s | %d | %.1f  | %d  | %d  | %.1f  | %.1f  | %s  |'  % (schedBlock.name, representativeTarget[3], representativeLongitudeValue, representativeLatitudeValue,
							representativeFrequencyValue, 
							representativeBandwidthValue, 
							band.replace('ALMA_RB_', ''), 
							SW, 
							# scienceGoal.performance.configurations,
							schedBlock.obsSchedBlockConstraints.minAngularResolutionValue, 
							schedBlock.obsSchedBlockConstraints.maxAngularResolutionValue, 
							schedBlock.arrayType, 
							schedBlock.executionCount, 
							schedBlock.integrationTimeValue, 
							representativeTarget[2], 
							len(listTargets),
							schedBlock.integrationTimeValue * len(listTargets), 
							schedBlock.executionCount * schedBlock.integrationTimeValue * len(listTargets),
							note)
						if schedBlock.arrayType == 'TWELVE-M':
							if schedBlock.integrationTimeValue > 50.:
								warnings += ('WARNING: ToS of SchedBlock %s is greater than 50.0 min\n' % (schedBlock.name))
						else:
							if schedBlock.integrationTimeValue > 35.:
								warnings += ('WARNING: ToS of SchedBlock %s is greater than 35.0 min\n' % (schedBlock.name))
						if fileOutput != None:
							fileOutput.write('| *%s*  | %s  | %s  | %s  | %5.1f  | %.1f  | %s | %s  | %.2f | %.2f | %s | %d | %.1f  | %d  | %d  | %.1f  | %.1f  | %s  |\n'  % (schedBlock.name, representativeTarget[3], representativeLongitudeValue, representativeLatitudeValue,
								representativeFrequencyValue, representativeBandwidthValue, band.replace('ALMA_RB_', ''), SW, schedBlock.obsSchedBlockConstraints.minAngularResolutionValue, schedBlock.obsSchedBlockConstraints.maxAngularResolutionValue, schedBlock.arrayType, schedBlock.executionCount, schedBlock.integrationTimeValue, representativeTarget[2], len(listTargets), schedBlock.integrationTimeValue * len(listTargets), schedBlock.executionCount * schedBlock.integrationTimeValue * len(listTargets), note))
						if args.all == True:
							for targetIndex in listTargets:
								if listTargets[targetIndex][0] != representativeLongitudeValue and listTargets[targetIndex][1] != representativeLatitudeValue:
									print '| | %s  | %s  | %s  | | | | | | | %d  | | | |' % (listTargets[targetIndex][3], listTargets[targetIndex][0], listTargets[targetIndex][1], listTargets[targetIndex][2])
									if fileOutput != None:
										fileOutput.write('| | %s  | %s  | %s  | | | | | | | %d  | | | |\n' % (listTargets[targetIndex][3], listTargets[targetIndex][0], listTargets[targetIndex][1], listTargets[targetIndex][2]))
									if listTargets[targetIndex][4] != 'J2000':
										warnings += ('WARNING: Target resource: %s in %s is in %s coordinates\n' % (listTargets[targetIndex][3], schedBlock.name, listTargets[targetIndex][4]))
						for targetIndex in listTargets:
							if listTargets[targetIndex][4] != 'J2000':
								warnings += ('WARNING: Target resource: %s in %s is in %s coordinates\n' % (listTargets[targetIndex][3], schedBlock.name, listTargets[targetIndex][4]))
					lastRepresentativeFrequencyValue = representativeFrequencyValue
					lastRepresentativeBandwidthValue = representativeBandwidthValue
					lastConfiguration = scienceGoal.performance.configurations
					lastIntergrationTime = schedBlock.integrationTimeValue
					lastrepresentativeLongitudeValue = representativeLongitudeValue
					lastRepresentativeLatitudeValue = representativeLatitudeValue
		for name in dictSB:
			if dictSB[name] > 1:
				warnings = 'WARNING: The SchedBlock name: %s is duplicated %d times\n' % (name, dictSB[name]) + warnings
		if len(warnings) > 0:
			print '\n%s' % warnings[:-1]
			if fileOutput != None:
				fileOutput.write('\n%s' % warnings)
	except aotError as error:
		print 'Error: %s' % error.description

fileOutput = None

parser = argparse.ArgumentParser(description = 'Descriptive information from AOT file for JIRA ticket')
parser.add_argument('-aot', nargs = 1, metavar = 'AOTfile', required = True, help = 'AOT File(s) to extract information')
parser.add_argument('-output', nargs = 1, metavar = 'outputFile', required = False, help = 'Specify filename of the output file')
parser.add_argument('-all', action = 'store_true', help = 'List all the source names')
parser.add_argument('-verbose', action = 'store_true')
args = parser.parse_args()

if args.output != None:
	if os.path.isdir(args.output[0]) == True:
		print 'The specified output file is a directory'
		sys.exit(1)
	else:
		fileOutput = open(args.output[0], "w+")

if args.aot != None:
	for fileAOT in args.aot:
		printInfo(fileAOT, fileOutput)

if fileOutput != None:
	fileOutput.close
