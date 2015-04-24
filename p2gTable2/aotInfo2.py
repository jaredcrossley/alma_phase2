import zipfile
import sys
import time
import math
import copy
# import pickle
# import arrayResolution2

from xml.dom.minidom import parseString

#version 0.90 October 2012
#version 0.91 November 2012
#version 0.92 January 2012 DopplerCalcType
#version 1.00 January 2013 Change a Cycle2 structures

c = 299792.458 #km/s
LATITUDE_ALMA = -23.03
DEG2RAD = math.pi / 180.

# BLUE     = '\033[34m'
# RED      = '\033[31m' 
# GREEN    = '\033[32m'
# YELLOW   = '\033[33m'
# BLACK    = '\033[30m'
# CRIM     = '\033[36m'
# NO_COLOR = '\033[0m'

dictionaryUnitSet = {}
dictionarySchedBlock = {}
dictionaryObservationParameters = {'PntCal': 'sbl:PointingCalParameters', 
								   'Science': 'sbl:ScienceParameters', 
								   'BndCal': 'sbl:BandpassCalParameters', 
								   'PhsCal': 'sbl:PhaseCalParameters', 
								   'AtmCal': 'sbl:AtmosphericCalParameters', 
								   'AmpCal': 'sbl:AmplitudeCalParameters',
								   'DelCal': 'sbl:DelayCalParameters',
								   'FocCal': 'sbl:FocusCalParameters',
								   'PolCal': 'sbl:PolarizationCalParameters'}
dictSpectralType = {'full': 'Spectral line', 'continuum': 'Continuum', 'scan': 'Scan'}
dictPolarization = {'DOUBLE': 'Dual', 'SINGLE_X': 'Single-X', 'FULL': 'Full'}
dictCalibrationSetup = {'system': 'System', 'user': 'User'}

class aotInfo():
	"""docstring for Project"""
	def __init__(self, aotPath, levelProposal = 99, levelProject = 99):
		global dictionarySchedBlock
		self.aotPath = aotPath
		try:
			fileAOT = zipfile.ZipFile(self.aotPath ,"r")
			if levelProject > -1:
				xmlProjectNode = parseString(fileAOT.read("ObsProject.xml"))
			if levelProposal > -1:
				xmlProposalNode = parseString(fileAOT.read("ObsProposal.xml"))
		except:
			raise aotError('The AOT file is missing or misformat')
		if levelProject > 3:
			for schedBlockName in fileAOT.namelist():
				if schedBlockName.lower().startswith('schedblock'):
					xmlSchedBlock = fileAOT.read(schedBlockName)
					schedBlockXml = parseString(xmlSchedBlock)
					for schedBlockNode in schedBlockXml.getElementsByTagName('sbl:SchedBlockEntity'):
						dictionarySchedBlock[schedBlockNode.getAttribute('entityId')] = schedBlockXml
		if levelProject > -1:
			self.obsProject = Project(xmlProjectNode, levelProject)
			del xmlProjectNode
		if levelProposal > -1:
			self.obsProposal = Proposal(xmlProposalNode, levelProposal)
			del xmlProposalNode
		fileAOT.close()
		del fileAOT

	def getProject(self):
		return self.obsProject

	def getProposal(self):
		return self.obsProposal

	def getSchedBlockList(self):
		scienceGoalList = self.getScienceGoalsList()
		schedBlockList = {}
		for scienceGoalIndex in scienceGoalList.keys():
			for schedBlockIndex in scienceGoalList[scienceGoalIndex].obsUnitSets.schedBlocks.keys():
				schedBlockList[schedBlockIndex] = scienceGoalList[scienceGoalIndex].obsUnitSets.schedBlocks[schedBlockIndex]
		return schedBlockList

	def getSchedBlock(self, UID):
		schedBlockList = self.getSchedBlockList()
		if schedBlockList.has_key(UID) == True:
			return schedBlockList[UID]
		else:
			raise aotError('Schedule Block not Found')

class Proposal:
	def __init__(self, xml, levelProposal):
		i = 0
		self.obsScienceGoals = {}
		self.obsProposalFeedBack = None
		if levelProposal > 1:
			for obsScienceGoalNode in xml.getElementsByTagName('prj:ScienceGoal'):
				obsScienceGoal = ObsScienceGoalProposal(i, obsScienceGoalNode, levelProposal)
				self.obsScienceGoals[obsScienceGoal.index] = obsScienceGoal
				i += 1
		for proposalFeedbackNode in xml.getElementsByTagName('prp:ProposalFeedback'):
			self.obsProposalFeedBack = ObsProposalFeedBack(proposalFeedbackNode)

	def getScienceGoalsList(self):
		return self.obsScienceGoals

class ObsProposalFeedBack:
	def __init__(self, proposalFeedbackNode):
		self.ARC = ''
		for timeAllocationNode in proposalFeedbackNode.getElementsByTagName('prp:TimeAllocationBreakdown'):
			for executiveNode in timeAllocationNode.getElementsByTagName('prp:ExecutiveFraction'):
				if float(executiveNode.getElementsByTagName('prp:timeFraction')[0].firstChild.data) > 0:
					self.ARC = executiveNode.getAttribute('name')

class Project:
	def __init__(self, xml, levelProject):
		self.name = ''
		self.uid = ''
		self.code = ''
		self.pi = ''
		self.version = ''
		self.obsPrograms = {}
		for obsProjectNode in xml.getElementsByTagName('prj:ObsProject'):
			self.name = obsProjectNode.getElementsByTagName('prj:projectName')[0].firstChild.data.encode('ascii', 'ignore')
			self.uid = obsProjectNode.getElementsByTagName('prj:ObsProjectEntity')[0].getAttribute("entityId")
			self.code = obsProjectNode.getElementsByTagName('prj:code')[0].firstChild.data
			self.pi = obsProjectNode.getElementsByTagName('prj:pI')[0].firstChild.data
			self.version = obsProjectNode.getElementsByTagName('prj:version')[0].firstChild.data
			if levelProject > 0:
				for obsProgramNode in obsProjectNode.getElementsByTagName('prj:ObsProgram'):
					self.obsPrograms[0] = ObsProgram(obsProgramNode, levelProject)

	def getScienceGoalsList(self):
		return self.obsPrograms[0].obsScienceGoals

	def getSchedBlockList(self):
		scienceGoalList = self.getScienceGoalsList()
		schedBlockList = {}
		for scienceGoalIndex in scienceGoalList.keys():
			scienceGoal = scienceGoalList[scienceGoalIndex]
			if scienceGoal.obsUnitSets != None:
				for schedBlockIndex in scienceGoalList[scienceGoalIndex].obsUnitSets.schedBlocks.keys():
					schedBlockList[schedBlockIndex] = scienceGoalList[scienceGoalIndex].obsUnitSets.schedBlocks[schedBlockIndex]
		return schedBlockList

class ObsProgram:
	def __init__(self, programNode, levelProject):
		global dictionaryUnitSet   #		self.obsPlans = {}
		self.obsScienceGoals = {}
		i = 0
		if levelProject > 1:
			for obsPlanNode in programNode.getElementsByTagName('prj:ObsPlan'):
				for obsUnitSetNode in obsPlanNode.getElementsByTagName('prj:ObsUnitSet'):
					dictionaryUnitSet[obsUnitSetNode.getAttribute('entityPartId')] = obsUnitSetNode
			for obsScienceGoalNode in programNode.getElementsByTagName('prj:ScienceGoal'):
				obsScienceGoal = ObsScienceGoalProject(i, obsScienceGoalNode, levelProject)
				self.obsScienceGoals[obsScienceGoal.index] = obsScienceGoal
				del obsScienceGoal
				i += 1
	
class ObsScienceGoalProposal:
	def __init__(self, index, scienceGoalNode, level):
		self.index = index
		self.name = scienceGoalNode.getElementsByTagName('prj:name')[0].firstChild.data.encode('ascii', 'ignore')
		self.estimatedTotalTimeAOTValue = float(scienceGoalNode.getElementsByTagName('prj:estimatedTotalTime')[0].firstChild.data)    #Andreas
		self.estimatedTotalTimeAOTUnit = scienceGoalNode.getElementsByTagName('prj:estimatedTotalTime')[0].getAttribute('unit')
		self.transformEstimatedTotalTime()
		self.estimatedTotalTimeValue = self.estimatedTotalTimeAOTValue
		self.estimatedTotalTimeUnit = self.estimatedTotalTimeAOTUnit
		self.estimated12Time = 0.
		self.estimated7Time = 0.
		self.estimatedTPTime = 0.
		self.estimatedACATime = 0.
		self.performance = None
		self.spectralSetup = None
		self.receiverBand = '-'
		self.obsUnitSets = None
		self.obsTargetParameters = []
		self.calibrationSetup = ''
		targetParameter = None
		for requiredBandsNode in scienceGoalNode.getElementsByTagName('prj:requiredReceiverBands'):
			self.receiverBand = requiredBandsNode.firstChild.data
		for calibrationSetupParametersNode in scienceGoalNode.getElementsByTagName('prj:CalibrationSetupParameters'):
			self.calibrationSetup = dictCalibrationSetup[calibrationSetupParametersNode.getAttribute('selection')]
		if level > 2:
			for performanceNode in scienceGoalNode.getElementsByTagName('prj:PerformanceParameters'):
				self.performance = ObsPerformance(performanceNode)
			for spectralSetupNode in scienceGoalNode.getElementsByTagName('prj:SpectralSetupParameters'):
				self.spectralSetup = ObsSpectralSetup(spectralSetupNode)
			for targetNode in scienceGoalNode.getElementsByTagName('prj:TargetParameters'):
				targetParameter = ObsTargetParameter(targetNode, self.performance, scienceGoalNode.getElementsByTagName('prj:SpectralSetupParameters')[0])
				self.obsTargetParameters.append(targetParameter)
			for obsUnitSetRefNode in scienceGoalNode.getElementsByTagName('prj:ObsUnitSetRef'):
				if obsUnitSetRefNode.getAttribute('partId') in dictionaryUnitSet:
					self.obsUnitSets = ObsUnitSet(dictionaryUnitSet[obsUnitSetRefNode.getAttribute('partId')], targetParameter, level)
		self.calculateEstimatedTimes()

	def calculateEstimatedTimes(self):
		self.estimated12Time = 0.
		self.estimated7Time = 0.
		self.estimatedTPTime = 0.
		self.estimatedTotalTimeValue = self.estimatedTotalTimeAOTValue
		if self.performance.useACA == 'N' and self.performance.useTP == 'N':
			self.estimated12Time = self.estimatedTotalTimeValue
		elif self.performance.useACA == 'Y' and self.performance.useTP == 'N':
			self.estimated12Time = self.estimatedTotalTimeValue / 3.
			self.estimated7Time = self.estimatedTotalTimeValue / 2.
		elif self.performance.useACA == 'Y' and self.performance.useTP == 'Y':
			self.estimated12Time = self.estimatedTotalTimeValue / 5.
			self.estimated7Time = self.estimatedTotalTimeValue / 2.5
			self.estimatedTPTime = self.estimatedTotalTimeValue / 1.25
		self.estimatedACATime = max(self.estimated7Time, self.estimatedTPTime)
		self.estimatedTotalTimeValue = self.estimated12Time + self.estimatedACATime

	def transformEstimatedTotalTime(self):
		time = self.estimatedTotalTimeAOTValue
		if self.estimatedTotalTimeAOTUnit == 's':
			self.estimatedTotalTimeAOTValue = time / 3600.
		if self.estimatedTotalTimeAOTUnit == 'min':
			self.estimatedTotalTimeAOTValue = time / 60.
		if self.estimatedTotalTimeAOTUnit == 'h':
			self.estimatedTotalTimeAOTValue = time
		self.estimatedTotalTimeAOTUnit = 'h'

class ObsScienceGoalProject:
	def __init__(self, index, scienceGoalNode, level):
		self.index = index
		self.name = scienceGoalNode.getElementsByTagName('prj:name')[0].firstChild.data.encode('ascii', 'ignore')
		self.estimatedTotalTime = scienceGoalNode.getElementsByTagName('prj:estimatedTotalTime')[0].firstChild.data   #Andreas
		self.performance = None
		self.spectralSetup = None
		self.receiverBand = '-'
		self.obsUnitSets = None
		self.targetParameter = None
		targetParameter = None
		for requiredBandsNode in scienceGoalNode.getElementsByTagName('prj:requiredReceiverBands'):
			self.receiverBand = requiredBandsNode.firstChild.data
		if level > 2:
			for performanceNode in scienceGoalNode.getElementsByTagName('prj:PerformanceParameters'):
				self.performance = ObsPerformance(performanceNode)
			for spectralSetupNode in scienceGoalNode.getElementsByTagName('prj:SpectralSetupParameters'):
				self.spectralSetup = ObsSpectralSetup(spectralSetupNode)
			for targetNode in scienceGoalNode.getElementsByTagName('prj:TargetParameters'):
				self.targetParameter = ObsTargetParameter(targetNode, self.performance, scienceGoalNode.getElementsByTagName('prj:SpectralSetupParameters')[0])
			for obsUnitSetRefNode in scienceGoalNode.getElementsByTagName('prj:ObsUnitSetRef'):
				if obsUnitSetRefNode.getAttribute('partId') in dictionaryUnitSet:
					self.obsUnitSets = ObsUnitSet(dictionaryUnitSet[obsUnitSetRefNode.getAttribute('partId')], self.targetParameter, level)

class ObsPerformance():
	def __init__(self, performanceNode):
		nodeSensitivity = performanceNode.getElementsByTagName('prj:desiredSensitivity')[0]
		self.desiredSensitivityFrequencyMeasure = performanceNode.getAttribute('desiredSensitivityFrequencyMeasure')
		self.desiredSensitivityValue = float(performanceNode.getElementsByTagName('prj:desiredSensitivity')[0].firstChild.data)
		self.desiredSensitivityUnit = nodeSensitivity.getAttribute('unit')
		self.bandWidthUsed = performanceNode.getAttribute('desiredSensitivityFrequencyMeasure')
		self.transformSensitivity()
		self.desiredAngularResolutionValue = performanceNode.getElementsByTagName('prj:desiredAngularResolution')[0].firstChild.data
		self.desiredAngularResolutionUnit = performanceNode.getElementsByTagName('prj:desiredAngularResolution')[0].getAttribute('unit')
		self.transformAngular()
		self.desiredLargestScaleValue = performanceNode.getElementsByTagName('prj:desiredLargestScale')[0].firstChild.data
		self.desiredLargestScaleUnit = performanceNode.getElementsByTagName('prj:desiredLargestScale')[0].getAttribute('unit')
		self.transformLargestAngular()
		self.representativeFrequencyValue = performanceNode.getElementsByTagName('prj:representativeFrequency')[0].firstChild.data
		self.representativeFrequencyUnit = performanceNode.getElementsByTagName('prj:representativeFrequency')[0].getAttribute('unit')
		self.transformRepresentativeFrequency()
		self.desiredBandwidthValue = float(performanceNode.getElementsByTagName('prj:desiredSensitivityReferenceFrequencyWidth')[0].firstChild.data)
		self.desiredBandwidthUnit = performanceNode.getElementsByTagName('prj:desiredSensitivityReferenceFrequencyWidth')[0].getAttribute('unit')
		desiredSensitivityReferenceFrequencyWidth = self.desiredBandwidthValue
		self.transformBandWidth()
		self.useACA = 'N'
		self.useTP = 'N'
		self.isTimeConstrained = 'N'
		if performanceNode.getElementsByTagName('prj:useACA')[0].firstChild.data != 'false':
			self.useACA = 'Y'
		if performanceNode.getElementsByTagName('prj:useTP')[0].firstChild.data != 'false':
			self.useTP = 'Y'
		if str(performanceNode.getElementsByTagName('prj:isTimeConstrained')[0].firstChild.data) != 'false':
			self.isTimeConstrained = 'Y'	
		self.MASValue = 0.0
		self.MASUnit = ''
		self.totalPower = 'N'
		self.configurations = ''
		self.mostCompactConf = ''
		self.configurationLines = self.calculateConfigurationLines()

	def transformSensitivity(self):
		sensitivity = float(self.desiredSensitivityValue)
		if self.desiredSensitivityUnit == 'Jy':
			self.desiredSensitivityValue =  sensitivity * 1000
		if self.desiredSensitivityUnit == 'uJy':
			self.desiredSensitivityValue = sensitivity / 1000
		self.desiredSensitivityUnit = 'mJy'

	def transformAngular(self):
		angular = float(self.desiredAngularResolutionValue)
		if self.desiredAngularResolutionUnit == 'arcsec':
			self.desiredAngularResolutionValue = angular
		if self.desiredAngularResolutionUnit == 'arcmin':
			self.desiredAngularResolutionValue = angular * 60
		if self.desiredAngularResolutionUnit == 'deg':
			self.desiredAngularResolutionValue = angular * 3600
		self.desiredAngularResolutionUnit = 'arcsec'

	def transformLargestAngular(self):
		angular = float(self.desiredLargestScaleValue)
		if self.desiredLargestScaleUnit == 'arcsec':
			self.desiredLargestScaleValue = angular
		if self.desiredLargestScaleUnit == 'arcmin':
			self.desiredLargestScaleValue = angular * 60
		if self.desiredLargestScaleUnit == 'deg':
			self.desiredLargestScaleValue = angular * 3600
		self.desiredLargestScaleUnit = 'arcsec'

	def transformRepresentativeFrequency(self):
		speed = float(self.representativeFrequencyValue)
		if self.representativeFrequencyUnit == 'GHz':
			self.representativeFrequencyValue = speed * 1
		if self.representativeFrequencyUnit == 'MHz':
			self.representativeFrequencyValue = speed / 1000
		if self.representativeFrequencyUnit == 'kHz':
			self.representativeFrequencyValue = speed / 1000000
		if self.representativeFrequencyUnit == 'Hz':
			self.representativeFrequencyValue = speed / 1000000000
		self.representativeFrequencyUnit = 'GHz'

	def transformBandWidth(self):
		speed = float(self.desiredBandwidthValue)
		if self.desiredBandwidthUnit == 'Hz':
			self.desiredBandwidthValue = speed / 1000000
		if self.desiredBandwidthUnit == 'kHz':
			self.desiredBandwidthValue = speed / 1000
		if self.desiredBandwidthUnit == 'MHz':
			self.desiredBandwidthValue = speed * 1
		if self.desiredBandwidthUnit == 'GHz':
			self.desiredBandwidthValue = speed * 1000
		self.desiredBandwidthUnit = 'MHz'

	def calculateConfigurationLines(self):
		prima = self.representativeFrequencyValue / 100.
		ARprima = self.desiredAngularResolutionValue / prima
		LASprima = self.desiredLargestScaleValue / prima
		if ARprima >= 0.41 and ARprima < 0.57 and LASprima > 0.91:
			return 2
		elif ARprima >= 0.57 and ARprima < 0.75 and LASprima > 0.91:
			return 2
		elif ARprima >= 0.75 and ARprima < 1.11 and LASprima > 14.4:
			return 2
		elif ARprima >= 1.11 and ARprima < 1.40 and LASprima > 18.0:
			return 2
		elif ARprima >= 1.40 and ARprima < 2.04 and LASprima > 18.0:
			return 2
		elif ARprima >= 2.04 and ARprima < 3.73 and LASprima > 26.3:
			return 2
		elif ARprima >= 3.73 and ARprima < 7.46 and LASprima > 26.1:
			return 2
		else:
			return 1

class ObsSpectralSetup:
	def __init__(self, spectralSetupNode):
		self.spectralType = dictSpectralType[spectralSetupNode.getAttribute('type')]
		self.polarization = dictPolarization[spectralSetupNode.getAttribute('polarisation')]
		self.spectralWindows = {}
		self.numberSpectralWindows = 0
		for spectralWindowNode in spectralSetupNode.getElementsByTagName('prj:ScienceSpectralWindow'):
			if int(spectralWindowNode.getElementsByTagName('prj:groupIndex')[0].firstChild.data) not in self.spectralWindows:
				self.spectralWindows[int(spectralWindowNode.getElementsByTagName('prj:groupIndex')[0].firstChild.data)] = [None, None, None, None]	
			self.spectralWindows[int(spectralWindowNode.getElementsByTagName('prj:groupIndex')[0].firstChild.data)][int(spectralWindowNode.getElementsByTagName('prj:index')[0].firstChild.data)] = ObsSpectralWindow(spectralWindowNode)
		for baseband in self.spectralWindows:
			for window in self.spectralWindows[baseband]:
				if window != None:
					self.numberSpectralWindows += 1
		self.observationMode = 'Single'
		baseSpectralResolution = 0.
		for baseband in self.spectralWindows:
			for window in self.spectralWindows[baseband]:
				if window != None:
					baseSpectralResolution = window.resolutionValue
		for baseband in self.spectralWindows:
			for window in self.spectralWindows[baseband]:
				if window != None:
					baseSpectralResolution = window.resolutionValue
					if baseSpectralResolution != window.resolutionValue and window.resolutionValue > 0.:
						self.observationMode = 'Mixed'

	def calculateSkyFrequency(self, sourceVelocity, dopplerType):
		for baseband in self.spectralWindows:
			for window in self.spectralWindows[baseband]:
				if window != None:
					window.calculateSkyFrequency(sourceVelocity, dopplerType)
					if window.isRepresentativeWindow == True:
						self.representativeFrequencyValue = window.skyCenterFrequencyValue
						self.representativeFrequencyUnit = window.skyCenterFrequencyUnit
						self.representativeBandwidthValue = window.bandwidthValue
						self.representativeFrequencyUnit = window.bandwidthUnit

class ObsSpectralWindow:
	def __init__(self, spectralWindowNode):
		self.skyCenterFrequencyValue = 0.
		self.skyCenterFrequencyUnit = ''
		self.centerFrequencyValue = float(spectralWindowNode.getElementsByTagName('prj:centerFrequency')[0].firstChild.data)
		self.centerFrequencyUnit = spectralWindowNode.getElementsByTagName('prj:centerFrequency')[0].getAttribute('unit')
		self.bandwidthValue = float(spectralWindowNode.getElementsByTagName('prj:bandWidth')[0].firstChild.data) * 0.9375
		self.bandwidthUnit = spectralWindowNode.getElementsByTagName('prj:bandWidth')[0].getAttribute('unit')
		self.resolutionValue = float(spectralWindowNode.getElementsByTagName('prj:spectralResolution')[0].firstChild.data) * 2
		self.resolutionUnit = spectralWindowNode.getElementsByTagName('prj:spectralResolution')[0].getAttribute('unit')
		self.isRepresentativeWindow = spectralWindowNode.getElementsByTagName('prj:representativeWindow')[0].firstChild.data == 'true'
		self.isSkyFrequency = spectralWindowNode.getElementsByTagName('prj:isSkyFrequency')[0].firstChild.data == 'true'
		if self.isSkyFrequency == True:
			self.skyCenterFrequencyValue = float(spectralWindowNode.getElementsByTagName('prj:centerFrequency')[0].firstChild.data)
			self.skyCenterFrequencyUnit = spectralWindowNode.getElementsByTagName('prj:centerFrequency')[0].getAttribute('unit')
			self.transformSkyCenterFrequency()
		self.transformResolution()

	def calculateSkyFrequency(self, sourceVelocity, dopplerType):
		if self.isSkyFrequency == False:
			self.skyCenterFrequencyValue = skyFrequencyDoppler(self.centerFrequencyValue, sourceVelocity, dopplerType)
			self.transformSkyCenterFrequency()

	def transformSkyCenterFrequency(self):
			speed = float(self.skyCenterFrequencyValue)
			if self.skyCenterFrequencyUnit == 'GHz':
				self.skyCenterFrequencyValue = speed * 1
			if self.skyCenterFrequencyUnit == 'MHz':
				self.skyCenterFrequencyValue = speed / 1000
			if self.skyCenterFrequencyUnit == 'kHz':
				self.skyCenterFrequencyValue = speed / 1000000
			if self.skyCenterFrequencyUnit == 'Hz':
				self.skyCenterFrequencyValue = speed / 1000000000
			self.skyCenterFrequencyUnit = 'GHz'

	def transformResolution(self):
			speed = float(self.resolutionValue)
			if self.resolutionUnit == 'GHz':
				self.resolutionValue = speed * 1000
			if self.resolutionUnit == 'MHz':
				self.resolutionValue = speed * 1
			if self.resolutionUnit == 'kHz':
				self.resolutionValue = speed / 1000
			if self.resolutionUnit == 'Hz':
				self.resolutionValue = speed / 1000000
			self.resolutionUnit = 'MHz'
		
class ObsUnitSet:
	def __init__(self, unitSetNode, targetParameter, level):
		global dictionarySchedBlock
		self.schedBlocks = {}
		self.id = unitSetNode.getAttribute('entityPartId')
		self.name = unitSetNode.getElementsByTagName('prj:name')[0].firstChild.data.encode('ascii', 'ignore')
		self.OUSStatusRef = ''
		if level > 3:
			for nodeSchedBlockRef in unitSetNode.getElementsByTagName('prj:SchedBlockRef'):
				self.schedBlocks[nodeSchedBlockRef.getAttribute('entityId')] = SchedBlock(dictionarySchedBlock[nodeSchedBlockRef.getAttribute('entityId')], targetParameter, level)
			for OUSStatusRefNode in unitSetNode.getElementsByTagName('prj:OUSStatusRef'):
				self.OUSStatusRef = OUSStatusRefNode.getAttribute('entityId')

class SchedBlock:
	def __init__(self, schedBlockNode, targetParameter, level):
		self.id = schedBlockNode.getElementsByTagName('sbl:SchedBlockEntity')[0].getAttribute('entityId')
		self.name = schedBlockNode.getElementsByTagName('prj:name')[0].firstChild.data.encode('ascii', 'ignore')
		self.obsFieldSources = {}
		self.obsParameters = {}
		self.obsSpectralSpecs = {}
		self.obsTargets = {}
		self.observingGroup = {}
		self.obsSchedBlockConstraints = None
		self.integrationTimeValue = 0.
		self.integrationTimeUnit = 's'
		self.representativeFrequencyValue = 0.
		self.representativeFrequencyUnit = 'GHz'
		self.representativeBandwidthValue = 0.
		self.representativeBandwidthUnit = 'MHz'
		self.executionCount = 0
		self.arrayType = schedBlockNode.getElementsByTagName('prj:ObsUnitControl')[0].getAttribute('arrayRequested')
		for scienceParameterNode in schedBlockNode.getElementsByTagName('sbl:ScienceParameters'):
			self.integrationTimeValue = float(scienceParameterNode.getElementsByTagName('sbl:integrationTime')[0].firstChild.data)
			self.integrationTimeUnit = scienceParameterNode.getElementsByTagName('sbl:integrationTime')[0].getAttribute('unit')
			self.representativeFrequencyValue = float(scienceParameterNode.getElementsByTagName('sbl:representativeFrequency')[0].firstChild.data)
			self.representativeFrequencyUnit = scienceParameterNode.getElementsByTagName('sbl:representativeFrequency')[0].getAttribute('unit')
			self.representativeBandwidthValue = float(scienceParameterNode.getElementsByTagName('sbl:representativeBandwidth')[0].firstChild.data)
			self.representativeBandwidthUnit = scienceParameterNode.getElementsByTagName('sbl:representativeBandwidth')[0].getAttribute('unit')
		for schedulingConstraintsNode in schedBlockNode.getElementsByTagName('sbl:SchedulingConstraints'):
			self.obsSchedBlockConstraints = ObsSchedBlockConstraints(schedulingConstraintsNode)
		if level > 4:
			for fieldSourceNode in schedBlockNode.getElementsByTagName('sbl:FieldSource'):
				self.obsFieldSources[fieldSourceNode.getAttribute('entityPartId')] = ObsFieldSource(fieldSourceNode)
			for intentType in dictionaryObservationParameters.keys():
				for obsParameterNode in schedBlockNode.getElementsByTagName(dictionaryObservationParameters[intentType]):
					self.obsParameters[obsParameterNode.getAttribute('entityPartId')] = ObsParameter(obsParameterNode, intentType)
			for spectralSpecNode in schedBlockNode.getElementsByTagName('sbl:SpectralSpec'):
				self.obsSpectralSpecs[spectralSpecNode.getAttribute('entityPartId')] =  ObsSpectralSpec(spectralSpecNode, targetParameter, level)
			for targetNode in schedBlockNode.getElementsByTagName('sbl:Target'):
				obsFieldSource = targetNode.getElementsByTagName('sbl:FieldSourceRef')[0].getAttribute('partId')
				obsParameter = targetNode.getElementsByTagName('sbl:ObservingParametersRef')[0].getAttribute('partId')
				obsSpectralSpec = targetNode.getElementsByTagName('sbl:AbstractInstrumentSpecRef')[0].getAttribute('partId')
				if self.obsSpectralSpecs[obsSpectralSpec].skyCenterFrequencyValue > 0:
					self.obsFieldSources[obsFieldSource].beamSizeValue = (1.2 * c / (12 * self.obsSpectralSpecs[obsSpectralSpec].skyCenterFrequencyValue * 1000000)) * 3600 * 57
					self.obsFieldSources[obsFieldSource].calculateTotalPoints()
				self.obsTargets[targetNode.getAttribute('entityPartId')] = ObsTarget(targetNode, self.obsFieldSources[obsFieldSource], self.obsParameters[obsParameter], copy.copy(self.obsSpectralSpecs[obsSpectralSpec]))
				del obsFieldSource
				del obsParameter
				del obsSpectralSpec
			for observingGroupNode in schedBlockNode.getElementsByTagName('sbl:ObservingGroup'):
				self.observingGroup[int(observingGroupNode.getElementsByTagName('sbl:index')[0].firstChild.data)] = ObservingGroup(observingGroupNode, self.obsTargets)
			for schedBlockControlNode in schedBlockNode.getElementsByTagName('sbl:SchedBlockControl'):
				self.executionCount = float(schedBlockControlNode.getElementsByTagName('sbl:executionCount')[0].firstChild.data)
		self.transformIntegrationTime()
		self.transformRepresentativeFrequency()
		self.transformRepresentativeBandwidth()

	def transformIntegrationTime(self):
		time = float(self.integrationTimeValue)
		if self.integrationTimeUnit == 's':
			self.integrationTimeValue = time / 60
		if self.integrationTimeUnit == 'min':
			self.integrationTimeValue = time
		if self.integrationTimeUnit == 'h':
			self.integrationTimeValue = time * 60

	def transformResolution(self):
			speed = float(self.resolutionValue)
			if self.resolutionUnit == 'GHz':
				self.resolutionValue = speed * 1000000
			if self.resolutionUnit == 'MHz':
				self.resolutionValue = speed * 1000
			if self.resolutionUnit == 'kHz':
				self.resolutionValue = speed * 1
			if self.resolutionUnit == 'Hz':
				self.resolutionValue = speed / 1000
			self.resolutionUnit = 'kHz'

	def transformRepresentativeFrequency(self):
		speed = float(self.representativeFrequencyValue)
		if self.representativeFrequencyUnit == 'MHz':
			self.representativeFrequencyValue = speed / 1000
		if self.representativeFrequencyUnit == 'GHz':
			self.representativeFrequencyValue = speed * 1
		if self.representativeFrequencyUnit == 'kHz':
			self.representativeFrequencyValue = speed / 1000000
		if self.representativeFrequencyUnit == 'Hz':
			self.representativeFrequencyValue = speed / 1000000000
		self.representativeFrequencyUnit = 'GHz'

	def transformRepresentativeBandwidth(self):
		value = float(self.representativeBandwidthValue)
		if self.representativeBandwidthUnit == 'GHz':
			self.representativeBandwidthValue = value * 1000
		if self.representativeBandwidthUnit == 'MHz':
			self.representativeBandwidthValue = value * 1
		if self.representativeBandwidthUnit == 'kHz':
			self.representativeBandwidthValue = value / 1000
		if self.representativeBandwidthUnit == 'Hz':
			self.representativeBandwidthValue = value / 1000000
		self.representativeBandwidthUnit = 'MHz'

class ObsSchedBlockConstraints:
	def __init__(self, schedBlockConstraintNode):
		self.minAngularResolutionValue = float(schedBlockConstraintNode.getElementsByTagName('sbl:minAcceptableAngResolution')[0].firstChild.data)
		self.minAngularResolutionUnit = schedBlockConstraintNode.getElementsByTagName('sbl:minAcceptableAngResolution')[0].getAttribute('unit')
		self.maxAngularResolutionValue = float(schedBlockConstraintNode.getElementsByTagName('sbl:maxAcceptableAngResolution')[0].firstChild.data)
		self.maxAngularResolutionUnit = schedBlockConstraintNode.getElementsByTagName('sbl:maxAcceptableAngResolution')[0].getAttribute('unit')
		self.transformResolution()
		self.receiverBand = schedBlockConstraintNode.getAttribute('representativeReceiverBand')
		if self.maxAngularResolutionValue > 0 and self.minAngularResolutionValue > 0:
			self.calcARValue = (self.minAngularResolutionValue + self.maxAngularResolutionValue) / 2
			self.calcARUnit = 'arcsec'
			self.calcLASValue = (self.maxAngularResolutionValue - self.minAngularResolutionValue) / 2
			self.calcLASUnit = 'arcsec'
		else:
			self.calcARValue = 0.
			self.calcARUnit = 'arcsec'			
			self.calcLASValue = 0.
			self.calcLASUnit = 'arcsec'
		self.system = ''
		self.latitudeValue = 0.
		self.latitudeUnit = ''
		self.longitudeValue = 0.
		self.longitudeUnit = ''
		self.representativeFrequencyValue = 0.
		self.representativeFrequencyUnit = 'GHz'
		for representativeCoordinatesNode in schedBlockConstraintNode.getElementsByTagName('sbl:representativeCoordinates'):
			self.system = representativeCoordinatesNode.getAttribute('system')
			self.longitudeValue = float(representativeCoordinatesNode.getElementsByTagName('val:longitude')[0].firstChild.data)
			self.longitudeUnit = representativeCoordinatesNode.getElementsByTagName('val:longitude')[0].getAttribute('unit')
			self.latitudeValue = float(representativeCoordinatesNode.getElementsByTagName('val:latitude')[0].firstChild.data)
			self.latitudeUnit = representativeCoordinatesNode.getElementsByTagName('val:latitude')[0].getAttribute('unit')
		for representativeFrequencyNode in schedBlockConstraintNode.getElementsByTagName('sbl:representativeFrequency'):
			self.representativeFrequencyValue = float(representativeFrequencyNode.firstChild.data)
			self.representativeFrequencyUnit = representativeFrequencyNode.getAttribute('unit')
		self.transformRepresentativeFrequency()

	def transformResolution(self):
		value = float(self.minAngularResolutionValue)
		if self.minAngularResolutionUnit == 'arcsec':
			self.minAngularResolutionValue = value
		if self.minAngularResolutionUnit == 'arcmin':
			self.minAngularResolutionValue = value * 60
		if self.minAngularResolutionUnit == 'deg':
			self.minAngularResolutionValue = value * 3600
		self.minAngularResolutionUnit = 'arcsec'

		value = float(self.maxAngularResolutionValue)
		if self.maxAngularResolutionUnit == 'arcsec':
			self.maxAngularResolutionValue = value
		if self.maxAngularResolutionUnit == 'arcmin':
			self.maxAngularResolutionValue = value * 60
		if self.maxAngularResolutionUnit == 'deg':
			self.maxAngularResolutionValue = value * 3600
		self.maxAngularResolutionUnit = 'arcsec'

	def transformRepresentativeFrequency(self):
		speed = float(self.representativeFrequencyValue)
		if self.representativeFrequencyUnit == 'MHz':
			self.representativeFrequencyValue = speed / 1000
		if self.representativeFrequencyUnit == 'GHz':
			self.representativeFrequencyValue = speed * 1
		if self.representativeFrequencyUnit == 'kHz':
			self.representativeFrequencyValue = speed / 1000000
		if self.representativeFrequencyUnit == 'Hz':
			self.representativeFrequencyValue = speed / 1000000000
		self.representativeFrequencyUnit = 'GHz'

class ObsFieldSource:
	def __init__(self, fieldSourceNode):
		self.id = fieldSourceNode.getAttribute('entityPartId')
		self.name = ''
		for nameNode in fieldSourceNode.getElementsByTagName('sbl:sourceName'):
			if nameNode.firstChild != None:
				self.name = nameNode.firstChild.data.encode('ascii', 'ignore')
		self.longitudeValue = 0.0
		self.longitudeUnit = ''
		self.latitudeValue = 0.0
		self.latitudeUnit = ''
		self.searchRadiusValue = 0.
		self.searchRadiusUnit = ''
		self.system = ''
		self.sourceVelocityValue = 0.0
		self.sourceVelocityUnit = 'km/s'
		self.dopplerCalcType = ''
		self.isQuery = False
		self.totalPoints = 0
		self.correctionFactor = 1
		self.beamSizeValue = 0
		self.beamSizeUnit = 'arcsec'
		self.longValue = 0
		self.longUnit = 'arcsec'
		self.shortValue = 0
		self.shortUnit = 'arcsec'
		self.spacingValue = 0
		self.spacingUnit = 'arcsec'
		self.patternType = ''
		self.multiPoints = []

		for isQueryNode in fieldSourceNode.getElementsByTagName('sbl:isQuery'):
			self.isQuery = isQueryNode.firstChild.data == 'true'
		if self.isQuery == True:
			for querySourceNode in fieldSourceNode.getElementsByTagName('sbl:QuerySource'):
				for queryCenterNode in querySourceNode.getElementsByTagName('sbl:queryCenter'):
					self.longitudeValue = float(queryCenterNode.getElementsByTagName('val:longitude')[0].firstChild.data)
					self.longitudeUnit = queryCenterNode.getElementsByTagName('val:longitude')[0].getAttribute('unit')
					self.latitudeValue = float(queryCenterNode.getElementsByTagName('val:latitude')[0].firstChild.data)
					self.latitudeUnit = queryCenterNode.getElementsByTagName('val:latitude')[0].getAttribute('unit')
					self.system = queryCenterNode.getAttribute('system')
				self.searchRadiusValue = float(querySourceNode.getElementsByTagName('sbl:searchRadius')[0].firstChild.data)
				self.searchRadiusUnit = querySourceNode.getElementsByTagName('sbl:searchRadius')[0].getAttribute('unit')
		else:
			coordinatesNode = fieldSourceNode.getElementsByTagName('sbl:sourceCoordinates')[0]
			if coordinatesNode != None:
				self.longitudeValue = float(coordinatesNode.getElementsByTagName('val:longitude')[0].firstChild.data)
				self.longitudeUnit = coordinatesNode.getElementsByTagName('val:longitude')[0].getAttribute('unit')
				self.latitudeValue = float(coordinatesNode.getElementsByTagName('val:latitude')[0].firstChild.data)
				self.latitudeUnit = coordinatesNode.getElementsByTagName('val:latitude')[0].getAttribute('unit')
				self.system = coordinatesNode.getAttribute('system')
		for sourceVelocityNode in fieldSourceNode.getElementsByTagName('sbl:sourceVelocity'):
			self.dopplerCalcType = sourceVelocityNode.getAttribute('dopplerCalcType')
			self.sourceVelocityValue = float(sourceVelocityNode.getElementsByTagName('val:centerVelocity')[0].firstChild.data)
			self.sourceVelocityUnit = sourceVelocityNode.getElementsByTagName('val:centerVelocity')[0].getAttribute('unit')
		for pointingPatternNode in fieldSourceNode.getElementsByTagName('sbl:PointingPattern'):
			self.patternType = 'point'
			for phaseCenterCoordinatesNode in pointingPatternNode.getElementsByTagName('sbl:phaseCenterCoordinates'):
				self.totalPoints += 1
				typeCoordinate = phaseCenterCoordinatesNode.getAttribute('type')
				name = ''
				for nameNode in phaseCenterCoordinatesNode.getElementsByTagName('val:fieldName'):
					name = nameNode.firstChild.data
				pointLongitudeValue = float(phaseCenterCoordinatesNode.getElementsByTagName('val:longitude')[0].firstChild.data)
				pointLongitudeUnit = phaseCenterCoordinatesNode.getElementsByTagName('val:longitude')[0].getAttribute('unit')
				pointLatitudeValue = float(phaseCenterCoordinatesNode.getElementsByTagName('val:latitude')[0].firstChild.data)
				pointLatitudeUnit = phaseCenterCoordinatesNode.getElementsByTagName('val:latitude')[0].getAttribute('unit')
				point = SinglePoint(name, typeCoordinate, pointLongitudeValue, pointLongitudeUnit, pointLatitudeValue, pointLatitudeUnit, float(self.longitudeValue), float(self.latitudeValue))
				self.multiPoints.append(point)


					# pointCoordinates = singlePointNode.getElementsByTagName('prj:centre')[0]
					# if pointCoordinates != None:
					# 	typeCoordinate = pointCoordinates.getAttribute('type')
					# 	name = ''
					# 	for nameNode in pointCoordinates.getElementsByTagName('val:fieldName'):
					# 		name = nameNode.firstChild.data
					# 	pointLongitudeValue = pointCoordinates.getElementsByTagName('val:longitude')[0].firstChild.data
					# 	pointLongitudeUnit = pointCoordinates.getElementsByTagName('val:longitude')[0].getAttribute('unit')
					# 	pointLatitudeValue = pointCoordinates.getElementsByTagName('val:latitude')[0].firstChild.data
					# 	pointLatitudeUnit = pointCoordinates.getElementsByTagName('val:latitude')[0].getAttribute('unit')
					# 	point = SinglePoint(name, typeCoordinate, float(pointLongitudeValue), pointLongitudeUnit, float(pointLatitudeValue), pointLatitudeUnit, float(targetObs.longitudeValue), float(targetObs.latitudeValue))
					# 	targetObs.multiPoints.append(point)

		for rectanglePatternNode in fieldSourceNode.getElementsByTagName('sbl:RectanglePattern'):
			self.patternType = 'rectangle'
			self.longValue = float(rectanglePatternNode.getElementsByTagName('sbl:longitudeLength')[0].firstChild.data)
			self.longUnit = rectanglePatternNode.getElementsByTagName('sbl:longitudeLength')[0].getAttribute('unit')
			self.shortValue = float(rectanglePatternNode.getElementsByTagName('sbl:latitudeLength')[0].firstChild.data)
			self.shortUnit = rectanglePatternNode.getElementsByTagName('sbl:latitudeLength')[0].getAttribute('unit')
			self.spacingValue = float(rectanglePatternNode.getElementsByTagName('sbl:orthogonalStep')[0].firstChild.data)
			self.spacingUnit = rectanglePatternNode.getElementsByTagName('sbl:orthogonalStep')[0].getAttribute('unit')
			self.transformRectangle()
		self.transformCoordinates()
		self.transformSourceVelocity()

	def transformSourceVelocity(self):
		if self.sourceVelocityUnit == 'm/s':
			self.sourceVelocityValue = self.sourceVelocity / 1000
			self.sourceVelocityUnit = 'km/s'

	def transformCoordinates(self):
		value = float(self.longitudeValue)
		if self.longitudeUnit == 'arcsec':
			self.longitudeValue = value / 3600
		if self.longitudeUnit == 'arcmin':
			self.longitudeValue = value / 60
		if self.longitudeUnit == 'deg':
			self.longitudeValue = value
		self.longitudeUnit = 'arcsec'

		value = float(self.latitudeValue)
		if self.latitudeUnit == 'arcsec':
			self.latitudeValue = value / 3600
		if self.latitudeUnit == 'arcmin':
			self.latitudeValue = value / 60
		if self.latitudeUnit == 'deg':
			self.latitudeValue = value
		self.latitudeUnit = 'arcsec'

	def transformRectangle(self):
		value = float(self.longValue)
		if self.longUnit == 'arcsec':
			self.longValue = value
		if self.longUnit == 'arcmin':
			self.longValue = value * 60
		if self.longUnit == 'deg':
			self.longValue = value * 3600
		self.longUnit = 'arcsec'

		value = float(self.shortValue)
		if self.shortUnit == 'arcsec':
			self.shortValue = value
		if self.shortUnit == 'arcmin':
			self.shortValue = value * 60
		if self.shortUnit == 'deg':
			self.shortValue = value * 3600
		self.shortUnit = 'arcsec'

		value = float(self.spacingValue)
		if self.spacingUnit == 'arcsec':
			self.spacingValue = value
		if self.spacingUnit == 'arcmin':
			self.spacingValue = value * 60
		if self.spacingUnit == 'deg':
			self.spacingValue = value * 3600
		self.spacingUnit = 'arcsec'

	def calculateTotalPoints(self):
		if self.patternType == 'rectangle':
			self.spacingValue = self.spacingValue / self.beamSizeValue
			if (self.beamSizeValue * self.spacingValue) != 0:
				x1 = int(self.longValue / (self.beamSizeValue * self.spacingValue))
			else:
				x1 = 0
			if (self.beamSizeValue * self.spacingValue) != 0:
				y1 = int(0.5 * (int(self.shortValue / (self.beamSizeValue * self.spacingValue)) + 2))
			else:
				y1 = 0
			self.totalPoints = (x1 + 1) * y1 + x1 * (y1 + 1)
			self.correctionFactor = (2 ** 0.5) * self.spacingValue + (-0.3562)

class ObsParameter:
	def __init__(self, obsParameterNode, intentType):
		self.id = obsParameterNode.getAttribute('entityPartId')
		self.typeParameter = intentType
		try:
			cycleTimeNode = obsParameterNode.getElementsByTagName('sbl:cycleTime')[0]
			self.cycleTimeValue = convertTimeToSec(float(cycleTimeNode.firstChild.data), cycleTimeNode.getAttribute('unit'))
			self.cycleTimeUnit = 's'
			del cycleTimeNode
		except:
			self.cycleTimeValue = 0.0
			self.cycleTimeUnit = ''

		try:
			subScanNode = obsParameterNode.getElementsByTagName('sbl:subScanDuration')[0]
			self.subScanTimeValue = convertTimeToSec(float(subScanNode.firstChild.data), subScanNode.getAttribute('unit'))
			self.subScanTimeUnit = 's'
			del subScanNode
		except:
			self.subScanTimeValue = 0.0
			self.subScanTimeUnit = ''

		try:
			subScanNode = obsParameterNode.getElementsByTagName('sbl:subScanDuration')[0]
			self.subScanTimeValue = convertTimeToSec(float(subScanNode.firstChild.data), subScanNode.getAttribute('unit'))
			self.subScanTimeUnit = 's'
			del subScanNode
		except:
			self.subScanTimeValue = 0.0
			self.subScanTimeUnit = ''

		try:
			integrationNode = obsParameterNode.getElementsByTagName('sbl:defaultIntegrationTime')[0]
			self.integrationTimeValue = convertTimeToSec(float(integrationNode.firstChild.data), integrationNode.getAttribute('unit'))
			self.integrationTimeUnit = 's'
			del integrationNode
		except:
			self.integrationTimeValue = 0.0
			self.integrationTimeUnit = ''

		try:
			representativeBandwidthNode = obsParameterNode.getElementsByTagName('sbl:representativeBandwidth')[0]
			self.representativeBandwidthValue = float(representativeBandwidthNode.firstChild.data)
			self.representativeBandwidthUnit = representativeBandwidthNode.getAttribute('unit')
			del representativeBandwidthNode
		except:
			self.representativeBandwidthValue = 0.0
			self.representativeBandwidthUnit = ''

		try:
			representativeFrequencyNode = obsParameterNode.getElementsByTagName('sbl:representativeFrequency')[0]
			self.representativeFrequencyValue = float(representativeFrequencyNode.firstChild.data)
			self.representativeFrequencyUnit = representativeFrequencyNode.getAttribute('unit')
			del representativeFrequencyNode
		except:
			self.representativeFrequencyValue = 0.0
			self.representativeFrequencyUnit = ''

		try:
			sensitivityNode = obsParameterNode.getElementsByTagName('sbl:sensitivityGoal')[0]
			self.sensitivityValue = float(sensitivityNode.firstChild.data)
			self.sensitivityUnit = sensitivityNode.getAttribute('unit')
			del sensitivityNode
		except:
			self.sensitivityValue = 0.0
			self.sensitivityUnit = ''

class ObsTarget:
	def __init__(self, targetNode, fieldSourceNode, parameterNode, spectralSpecNode):
		self.id = targetNode.getAttribute('entityPartId')
		self.obsFieldSource = fieldSourceNode
		self.obsParameter = parameterNode
		self.obsSpectralSpec = spectralSpecNode
		self.obsSpectralSpec.calculateSkyFrequency(self.obsFieldSource.sourceVelocityValue)

class ObsTargetParameter:
	def __init__(self, targetNode, performanceParameters, spectralSetupNode):
		self.id = targetNode.getAttribute('entityPartId')
		if targetNode.getElementsByTagName('prj:sourceName')[0].firstChild != None:
			self.name = targetNode.getElementsByTagName('prj:sourceName')[0].firstChild.data
		else:
			self.name = ''
		self.sourceVelocityValue = 0.0
		self.sourceVelocityUnit = 'km/s'
		self.dopplerCalcType = ''
		self.system = ''
		self.latitudeValue = 0.0
		self.latitudeUnit = ''
		self.longitudeValue = 0.0
		self.longitudeUnit = ''
		self.targetType = targetNode.getAttribute('type')
		self.beamSizeValue = (1.2 * c / (12 * performanceParameters.representativeFrequencyValue * 1000000)) * 3600 * 57
		self.beamSizeUnit = 'arcsec'
		self.totalPoints = 0
		self.longValue = 0.
		self.longUnit = ''
		self.shortValue = 0.
		self.shortUnit = ''
		self.pALongValue = 0.
		self.pALongUnit = ''
		self.spacingValue = 0.
		self.spacingUnit = ''
		self.multiPoints = []
		self.spectralSetup = ObsSpectralSetup(spectralSetupNode)

		for sourceCoordinates in targetNode.getElementsByTagName('prj:sourceCoordinates'):
			self.system = sourceCoordinates.getAttribute('system')
			self.longitudeValue = float(sourceCoordinates.getElementsByTagName('val:longitude')[0].firstChild.data)
			self.longitudeUnit = sourceCoordinates.getElementsByTagName('val:longitude')[0].getAttribute('unit')
			self.latitudeValue = float(sourceCoordinates.getElementsByTagName('val:latitude')[0].firstChild.data)
			self.latitudeUnit = sourceCoordinates.getElementsByTagName('val:latitude')[0].getAttribute('unit')

		for sourceVelocityNode in targetNode.getElementsByTagName('prj:sourceVelocity'):
			nodeCenterVelocity = sourceVelocityNode.getElementsByTagName('val:centerVelocity')
			self.sourceVelocityValue = float(nodeCenterVelocity[0].firstChild.data)
			self.sourceVelocityUnit = nodeCenterVelocity[0].getAttribute('unit')
			self.dopplerCalcType = sourceVelocityNode.getAttribute('dopplerCalcType')
			self.transformSourceVelocity()
			del nodeCenterVelocity

		if self.targetType == 'F_MultiplePoints':
			for singlePointNode in targetNode.getElementsByTagName('prj:SinglePoint'):
				self.totalPoints += 1
				self.correctionFactor = 1
				self.isMultiPoint = True
				pointCoordinates = singlePointNode.getElementsByTagName('prj:centre')[0]
				if pointCoordinates != None:
					typeCoordinate = pointCoordinates.getAttribute('type')
					name = ''
					for nameNode in pointCoordinates.getElementsByTagName('val:fieldName'):
						name = nameNode.firstChild.data
					pointLongitudeValue = pointCoordinates.getElementsByTagName('val:longitude')[0].firstChild.data
					pointLongitudeUnit = pointCoordinates.getElementsByTagName('val:longitude')[0].getAttribute('unit')
					pointLatitudeValue = pointCoordinates.getElementsByTagName('val:latitude')[0].firstChild.data
					pointLatitudeUnit = pointCoordinates.getElementsByTagName('val:latitude')[0].getAttribute('unit')
					point = SinglePoint(name, typeCoordinate, float(pointLongitudeValue), pointLongitudeUnit, float(pointLatitudeValue), pointLatitudeUnit, float(self.longitudeValue), float(self.latitudeValue))
					self.multiPoints.append(point)

		if self.targetType == 'F_SingleRectangle':
			for nodeRectangle in targetNode.getElementsByTagName('prj:Rectangle'):
				self.longValue = float(nodeRectangle.getElementsByTagName('prj:long')[0].firstChild.data)
				self.longUnit = nodeRectangle.getElementsByTagName('prj:long')[0].getAttribute('unit')
				self.shortValue = float(nodeRectangle.getElementsByTagName('prj:short')[0].firstChild.data)
				self.shortUnit = nodeRectangle.getElementsByTagName('prj:short')[0].getAttribute('unit')
				self.pALongValue = float(nodeRectangle.getElementsByTagName('prj:pALong')[0].firstChild.data)
				self.pALongUnit = nodeRectangle.getElementsByTagName('prj:pALong')[0].getAttribute('unit')
				self.transformRectangle()
				self.spacingValue = nodeRectangle.getElementsByTagName('prj:spacing')[0].firstChild.data
				self.spacingUnit = nodeRectangle.getElementsByTagName('prj:spacing')[0].getAttribute('unit')
				self.transformSpacing()
				self.spacingValue = self.spacingValue / self.beamSizeValue
				x1 = int(self.longValue / (self.beamSizeValue * self.spacingValue))
				y1 = int(0.5 * (int(self.shortValue / (self.beamSizeValue * self.spacingValue)) + 2))
				self.totalPoints = (x1 + 1) * y1 + x1 * (y1 + 1)
				self.correctionFactor = (2 ** 0.5) * self.spacingValue + (-0.3562)

		self.spectralSetup.calculateSkyFrequency(self.sourceVelocityValue, self.dopplerCalcType)
		
		if performanceParameters.desiredSensitivityFrequencyMeasure == 'FinestResolution':
			SR = [9999999., 9999999., 9999999., 9999999.]
			SRU = ''
			for spectralWindow in self.spectralSetup.spectralWindows:
				for window in self.spectralSetup.spectralWindows[spectralWindow]:
					if window != None:
						SR[spectralWindow] = window.resolutionValue
						SRU = window.resolutionUnit
			performanceParameters.desiredBandwidthValue = min(SR)
			performanceParameters.desiredBandwidthUnit = SRU
		elif performanceParameters.desiredSensitivityFrequencyMeasure == 'AggregateBandWidth':
			SR = 0.
			for spectralWindow in self.spectralSetup.spectralWindows:
				for window in self.spectralSetup.spectralWindows[spectralWindow]:
					if window != None:
						SR += window.bandwidthValue
						SRU = window.bandwidthUnit
			performanceParameters.desiredBandwidthValue = SR
			performanceParameters.desiredBandwidthUnit = SRU
		elif performanceParameters.desiredSensitivityFrequencyMeasure == 'LargestWindowBandWidth':
			SR = [0., 0., 0., 0.]
			SRU = ''
			for spectralWindow in self.spectralSetup.spectralWindows:
				for window in self.spectralSetup.spectralWindows[spectralWindow]:
					if window != None:
						SR[spectralWindow] = window.bandwidthValue
						SRU = window.bandwidthUnit
			performanceParameters.desiredBandwidthValue = max(SR)
			performanceParameters.desiredBandwidthUnit = SRU
		performanceParameters.transformBandWidth()

	def transformSourceVelocity(self):
		if self.sourceVelocityUnit == 'm/s':
			self.sourceVelocityValue = self.sourceVelocity / 1000
			self.sourceVelocityUnit = 'km/s'

	def transformRectangle(self):
		value = float(self.longValue)
		if self.longUnit == 'arcsec':
			self.longValue = value
		if self.longUnit == 'arcmin':
			self.longValue = value * 60
		if self.longUnit == 'deg':
			self.longValue = value * 3600
		self.longUnit = 'arcsec'

		value = float(self.shortValue)
		if self.shortUnit == 'arcsec':
			self.shortValue = value
		if self.shortUnit == 'arcmin':
			self.shortValue = value * 60
		if self.shortUnit == 'deg':
			self.shortValue = value * 3600
		self.shortUnit = 'arcsec'

	def transformSpacing(self):
		value = float(self.spacingValue)
		if self.spacingUnit == 'arcsec':
			self.spacingValue = value
		if self.spacingUnit == 'arcmin':
			self.spacingValue = value * 60
		if self.spacingUnit == 'deg':
			self.spacingValue = value * 3600
		self.spacingUnit = 'arcsec'

class SinglePoint:
	def __init__(self, name, typeCoordinate, longitudeValue, longitudeUnit, latitudeValue, latitudeUnit, centerLongitudeValue, centerLatitudeValue):
		self.name = name
		self.longitudeValue = longitudeValue
		self.longitudeUnit = longitudeUnit
		self.latitudeValue = latitudeValue
		self.latitudeUnit = latitudeUnit
		if typeCoordinate == 'RELATIVE':
			self.transformCoordinates()
			self.longitudeValue = centerLongitudeValue + self.longitudeValue
			self.latitudeValue = centerLatitudeValue + self.latitudeValue

	def transformCoordinates(self):
		value = self.longitudeValue
		if self.longitudeUnit == 'arcsec':
			self.longitudeValue = value / 3600
		if self.longitudeUnit == 'arcmin':
			self.longitudeValue = value / 60
		self.longitudeUnit = 'deg'

		value = self.latitudeValue
		if self.latitudeUnit == 'arcsec':
			self.latitudeValue = value / 3600
		if self.latitudeUnit == 'arcmin':
			self.latitudeValue = value / 60
		self.latitudeUnit = 'deg'

class ObservingGroup:
	def __init__(self, observingGroupNode, obsTargets):
		self.index = int(observingGroupNode.getElementsByTagName('sbl:index')[0].firstChild.data)
		self.name = observingGroupNode.getElementsByTagName('sbl:name')[0].firstChild.data.encode('ascii', 'ignore')
		self.obsOrdTargets = {}
		for orderedTargetNode in observingGroupNode.getElementsByTagName('sbl:OrderedTarget'):
			targetIndex = int(orderedTargetNode.getElementsByTagName('sbl:index')[0].firstChild.data)
			if obsTargets.has_key(orderedTargetNode.getElementsByTagName('sbl:TargetRef')[0].getAttribute('partId')) == True:
				obsTarget = obsTargets[orderedTargetNode.getElementsByTagName('sbl:TargetRef')[0].getAttribute('partId')]
			else:
				obsTarget = None
			self.obsOrdTargets[targetIndex] = ObsOrdTarget(targetIndex, obsTarget)
			del targetIndex
		
class ObsSpectralSpec:
	def __init__(self, spectralSpecNode, targetParameter, level):
		self.id = spectralSpecNode.getAttribute('entityPartId')
		self.name = spectralSpecNode.getElementsByTagName('sbl:name')[0].firstChild.data
		self.basebandSpecifications = {}
		self.receiverBand = ''
		self.restFrequencyValue = 0.
		self.restFrequencyUnit = ''
		self.dopplerReference = ''
		self.centerOffsetFrequencyValue = 0.
		self.centerOffsetFrequencyUnit = 'GHz'
		self.lo1FrequencyValue = 0.
		self.lo1FrequencyUnit = 'GHz'
		self.correlatorConfiguration = None
		for frequencySetupNode in spectralSpecNode.getElementsByTagName('sbl:FrequencySetup'):
			self.restFrequencyValue = float(frequencySetupNode.getElementsByTagName('sbl:restFrequency')[0].firstChild.data)
			self.restFrequencyUnit = frequencySetupNode.getElementsByTagName('sbl:restFrequency')[0].getAttribute('unit')
			self.lo1FrequencyValue = float(frequencySetupNode.getElementsByTagName('sbl:lO1Frequency')[0].firstChild.data)
			self.lo1FrequencyUnit = frequencySetupNode.getElementsByTagName('sbl:lO1Frequency')[0].getAttribute('unit')
			self.dopplerReference = frequencySetupNode.getAttribute('dopplerReference')
			self.receiverBand = frequencySetupNode.getAttribute('receiverBand')
			if level > 5:
				for basebandNode in frequencySetupNode.getElementsByTagName('sbl:BaseBandSpecification'):
					self.basebandSpecifications[basebandNode.getAttribute('entityPartId').encode('ascii', 'ignore')] = ObsBasebandSpecification(basebandNode, self.restFrequencyValue, targetParameter, self.dopplerReference, targetParameter.dopplerCalcType)
		self.noBaseBandSpecification = len(self.basebandSpecifications)
		self.transformRestFrequency()
		self.transformLO1Frequency()
		self.skyCenterFrequencyValue = skyFrequencyDoppler(self.restFrequencyValue, targetParameter.sourceVelocityValue, targetParameter.dopplerCalcType)
		self.skyCenterFrequencyUnit = 'GHz'
		if level > 5:
			for correlatorConfigurationNode in spectralSpecNode.getElementsByTagName('sbl:BLCorrelatorConfiguration'):
				self.correlatorConfiguration = ObsCorrelatorConfiguration(correlatorConfigurationNode)
			for correlatorConfigurationNode in spectralSpecNode.getElementsByTagName('sbl:ACACorrelatorConfiguration'):
				self.correlatorConfiguration = ObsCorrelatorConfiguration(correlatorConfigurationNode)
			if self.correlatorConfiguration != None:
				for baseBandConfigNode in self.correlatorConfiguration.blBaseBandConfigs:
					if baseBandConfigNode.baseBandSpecificationRef != None and baseBandConfigNode.baseBandSpecificationRef in self.basebandSpecifications:
						self.basebandSpecifications[baseBandConfigNode.baseBandSpecificationRef].centerOffsetFrequencyValue = baseBandConfigNode.offsetFrequencyValue
						self.basebandSpecifications[baseBandConfigNode.baseBandSpecificationRef].centerOffsetFrequencyUnit = baseBandConfigNode.offsetFrequencyUnit
						self.basebandSpecifications[baseBandConfigNode.baseBandSpecificationRef].centerOffsetFrequencySign = baseBandConfigNode.offsetFrequencySign

	def calculateSkyFrequency(self, sourceVelocity):
		for basebandIndex in self.basebandSpecifications:
			self.basebandSpecifications[basebandIndex].calculateSkyFrequency(sourceVelocity, self.lo1FrequencyValue)

	def transformRestFrequency(self):
			speed = float(self.restFrequencyValue)
			if self.restFrequencyUnit == 'GHz':
				self.restFrequencyValue = speed * 1
			if self.restFrequencyUnit == 'MHz':
				self.restFrequencyValue = speed / 1000
			if self.restFrequencyUnit == 'kHz':
				self.restFrequencyValue = speed / 1000000
			if self.restFrequencyUnit == 'Hz':
				self.restFrequencyValue = speed / 1000000000
			self.restFrequencyUnit = 'GHz'

	def transformLO1Frequency(self):
			value = float(self.lo1FrequencyValue)
			if self.lo1FrequencyUnit == 'GHz':
				self.lo1FrequencyValue = value * 1
			if self.lo1FrequencyUnit == 'MHz':
				self.lo1FrequencyValue = value / 1000
			if self.lo1FrequencyUnit == 'kHz':
				self.lo1FrequencyValue = value / 1000000
			if self.lo1FrequencyUnit == 'Hz':
				self.lo1FrequencyValue = value / 1000000000
			self.lo1FrequencyUnit = 'GHz'

class ObsBasebandSpecification:
	def __init__(self, basebandSpecificationNode, restFrequencyValue, targetParameter, dopplerReference, dopplerCalcType):
		self.id = basebandSpecificationNode.getAttribute('entityPartId')
		self.name = basebandSpecificationNode.getAttribute('baseBandName')
		self.centerFrequencyValue = float(basebandSpecificationNode.getElementsByTagName('sbl:centerFrequency')[0].firstChild.data)
		self.centerFrequencyUnit = basebandSpecificationNode.getElementsByTagName('sbl:centerFrequency')[0].getAttribute('unit')
		self.lo2FrequencyValue = float(basebandSpecificationNode.getElementsByTagName('sbl:lO2Frequency')[0].firstChild.data)
		self.lo2FrequencyUnit =  basebandSpecificationNode.getElementsByTagName('sbl:lO2Frequency')[0].getAttribute('unit')
		self.transformRestFrequency()
		self.centerOffsetFrequencyValue = 3.  #cambiar a 3
		self.centerOffsetFrequencyUnit = 'GHz'
		self.centerOffsetFrequencySign = 0
		self.skyFrequencyValue = 0.
		self.skyFrequencyUnit = 'GHz'
		self.skyFrequencyPureValue = 0.
		self.skyFrequencyPureUnit = 'GHz'
		self.dopplerReference = dopplerReference
		self.dopplerCalcType = dopplerCalcType

	def calculateSkyFrequency(self, sourceVelocity, lo1FrequencyValue):
		if self.dopplerReference == 'rest':
			self.skyFrequencyValue = skyFrequencyDoppler(self.centerFrequencyValue, sourceVelocity, self.dopplerCalcType)
		else:
			self.skyFrequencyValue = self.centerFrequencyValue
		self.skyFrequencyUnit = 'GHz'
		self.skyFrequencyPureValue = self.skyFrequencyValue
		self.skyFrequencyPureUnit = 'GHz'
		if self.skyFrequencyValue > lo1FrequencyValue:
			self.skyFrequencyPureValue = lo1FrequencyValue + self.lo2FrequencyValue - self.centerOffsetFrequencyValue
		else:
			self.skyFrequencyPureValue = lo1FrequencyValue - self.lo2FrequencyValue + self.centerOffsetFrequencyValue

	def transformRestFrequency(self):
			frequency = float(self.centerFrequencyValue)
			if self.centerFrequencyUnit == 'GHz':
				self.centerFrequencyValue = frequency * 1
			if self.centerFrequencyUnit == 'MHz':
				self.centerFrequencyValue = frequency / 1000
			if self.centerFrequencyUnit == 'kHz':
				self.centerFrequencyValue = frequency / 1000000
			if self.centerFrequencyUnit == 'Hz':
				self.centerFrequencyValue = frequency / 1000000000
			self.centerFrequencyUnit = 'GHz'

class ObsCorrelatorConfiguration:
	def __init__(self, blCorrelatorConfigurationNode):
		self.blBaseBandConfigs = []
		for blBaseBandConfigNode in blCorrelatorConfigurationNode.getElementsByTagName('sbl:BLBaseBandConfig'):
			self.blBaseBandConfigs.append(ObsBaseBandConfig(blBaseBandConfigNode))
		for blBaseBandConfigNode in blCorrelatorConfigurationNode.getElementsByTagName('sbl:ACABaseBandConfig'):
			self.blBaseBandConfigs.append(ObsBaseBandConfig(blBaseBandConfigNode))

class ObsBaseBandConfig:
	def __init__(self, blBaseBandConfigNode):
		self.baseBandSpecificationRef = None
		self.offsetFrequencyValue = 0.
		self.offsetFrequencyUnit = 'GHz'
		self.offsetFrequencySign = 0
		self.resolutionValue = 0.
		self.resolutionUnit = ''
		for baseBandSpecificationRefNode in blBaseBandConfigNode.getElementsByTagName('sbl:BaseBandSpecificationRef'):
			self.baseBandSpecificationRef = baseBandSpecificationRefNode.getAttribute('partId')
		for blSpectralWindowNode in blBaseBandConfigNode.getElementsByTagName('sbl:BLSpectralWindow'):
			self.offsetFrequencyValue = float(blSpectralWindowNode.getElementsByTagName('sbl:centerFrequency')[0].firstChild.data)
			self.offsetFrequencyUnit = blSpectralWindowNode.getElementsByTagName('sbl:centerFrequency')[0].getAttribute('unit')
			self.effectiveBandwidthValue = float(blSpectralWindowNode.getElementsByTagName('sbl:effectiveBandwidth')[0].firstChild.data)
			self.effectiveBandwidthUnit = blSpectralWindowNode.getElementsByTagName('sbl:effectiveBandwidth')[0].getAttribute('unit')
			self.transformBandWidth()
			self.effectiveNumberOfChannels = int(blSpectralWindowNode.getElementsByTagName('sbl:effectiveNumberOfChannels')[0].firstChild.data)
			self.resolutionValue = (self.effectiveBandwidthValue / self.effectiveNumberOfChannels) * 1000
			self.resolutionUnit = 'kHz'
			if blSpectralWindowNode.getAttribute('sideBand') == 'LSB':
				self.offsetFrequencySign = -1
			else:
				self.offsetFrequencySign = 1
			self.offsetFrequencySign
		for blSpectralWindowNode in blBaseBandConfigNode.getElementsByTagName('sbl:ACASpectralWindow'):
			self.offsetFrequencyValue = float(blSpectralWindowNode.getElementsByTagName('sbl:centerFrequency')[0].firstChild.data)
			self.offsetFrequencyUnit = blSpectralWindowNode.getElementsByTagName('sbl:centerFrequency')[0].getAttribute('unit')
			if blSpectralWindowNode.getAttribute('sideBand') == 'LSB':
				self.offsetFrequencySign = -1
			else:
				self.offsetFrequencySign = 1
			self.offsetFrequencySign
		self.transformOffsetFrequency()

	def transformOffsetFrequency(self):
			frequency = float(self.offsetFrequencyValue)
			if self.offsetFrequencyUnit == 'GHz':
				self.offsetFrequencyValue = frequency * 1
			if self.offsetFrequencyUnit == 'MHz':
				self.offsetFrequencyValue = frequency / 1000
			if self.offsetFrequencyUnit == 'kHz':
				self.offsetFrequencyValue = frequency / 1000000
			if self.offsetFrequencyUnit == 'Hz':
				self.offsetFrequencyValue = frequency / 1000000000
			self.offsetFrequencyUnit = 'GHz'

	def transformBandWidth(self):
		speed = float(self.effectiveBandwidthValue)
		if self.effectiveBandwidthUnit == 'MHz':
			self.effectiveBandwidthValue = speed * 1
		if self.effectiveBandwidthUnit == 'GHz':
			self.effectiveBandwidthValue = speed * 1000.
		if self.effectiveBandwidthUnit == 'kHz':
			self.effectiveBandwidthValue = speed / 1000.
		if self.effectiveBandwidthUnit == 'Hz':
			self.effectiveBandwidthValue = speed / 1000000.
		self.effectiveBandwidthUnit = 'MHz'

class ObsOrdTarget:
	def __init__(self, index, obsTarget):
		self.index = index
		self.obsTarget = obsTarget

class aotError(Exception):
	def __init__(self, value):
		self.description = value

def getArrayConfiguration(angularResolution, LAS, frequency, declination, useACA):
	import arrayResolution2
	ac = arrayResolution2.arrayRes([0, angularResolution, LAS, frequency, declination, useACA])
	ac.silentRun()
	tempConfigurations = ac.run()
	configuration1 = tempConfigurations[1].split(',')
	TP = 'N'
	if len(configuration1) > 6:
		TP = configuration1[7]
		configuration1 = [configuration1[0], configuration1[1], configuration1[2], configuration1[3], configuration1[4], configuration1[5], configuration1[6]]
		infoFound = False
		for data in range(7):
			if configuration1[data] != '':
				infoFound = True
		if infoFound == False:
			configuration1 = None
	else:
		configuration1 = None
	configuration2 = tempConfigurations[0].split(',')
	if len(configuration2) > 6:
		if TP == 'N':
			TP = configuration2[7]
		configuration2 = [configuration2[0], configuration2[1], configuration2[2], configuration2[3], configuration2[4], configuration2[5], configuration2[6]]
		infoFound = False
		for data in range(7):
			if configuration2[data] != '':
				infoFound = True
		if infoFound == False:
			configuration2 = None
	else:
		configuration2 = None
	return TP, [configuration1, configuration2]

def convertTimeToSec(TimeParam, UnitParam):
	timeSec = {'h': lambda TimeParam: TimeParam * 60 * 60,
			   'min': lambda TimeParam: TimeParam * 60,
			   's': lambda TimeParam: TimeParam} [UnitParam](TimeParam)
	return timeSec

def skyFrequencyDoppler(restFrequency, sourceVelocity, dopplerType):
	"""
		restFrequency in GHz, sourceVelocity in km/s
	"""
	skyFrequency = 0.
	if dopplerType == "RELATIVISTIC":
		skyFrequency = restFrequency * ((1 - (sourceVelocity / c) ** 2) ** 0.5) / (1 + (sourceVelocity / c))
	elif dopplerType == "RADIO":
		skyFrequency = float(restFrequency * (1 - (sourceVelocity / c)))
	elif dopplerType == "OPTICAL":
		skyFrequency = float(restFrequency * ((1 + (sourceVelocity / c)) ** -1))
	return skyFrequency

