#!/usr/bin/python
from datetime import datetime
import sys
sys.argv.append( '-b True' )
from ROOT import *
import array
import math
from optparse import OptionParser
tRand = TRandom3()
from random import randint
import os

##########################################################################################
#################      SETUP OPTIONS - File, Normalization, etc    #######################
##########################################################################################

# Input Options - file, cross-section, number of vevents
parser = OptionParser()
parser.add_option("-f", "--file", dest="filename", help="input root file", metavar="FILE")
parser.add_option("-b", "--batch", dest="dobatch", help="run in batch mode", metavar="BATCH")
parser.add_option("-s", "--sigma", dest="crosssection", help="specify the process cross-section", metavar="SIGMA")
parser.add_option("-n", "--ntotal", dest="ntotal", help="total number of MC events for the sample", metavar="NTOTAL")
parser.add_option("-l", "--lumi", dest="lumi", help="integrated luminosity for data taking", metavar="LUMI")
parser.add_option("-j", "--json", dest="json", help="json file for certified run:lumis", metavar="JSON")
parser.add_option("-d", "--dir", dest="dir", help="output directory", metavar="DIR")
parser.add_option("-p", "--pdf", dest="pdf", help="option to produce pdf uncertainties", metavar="PDF")


(options, args) = parser.parse_args()
dopdf = int(options.pdf)==1

# Here we get the file name, and adjust it accordingly for EOS, castor, or local directory
name = options.filename
if '/store' in name:
	name = 'root://eoscms//eos/cms'+name
if '/castor/cern.ch' in name:
	name = 'rfio://'+name

# These are switches based on the tag name. 
# First is whether to change out a muon with an electron ( for e-mu ttbar samples)
emuswitch=False
if "EMuSwitch" in options.dir:
	emuswitch=True
# Turn of the isolation condition for QCD studies
nonisoswitch=False
if "NonIso" in options.dir:
	nonisoswitch = True
# Quick test means no systematics
quicktestswitch = False
if "QuickTest" in options.dir:
	quicktestswitch = True
# Modifications of muon pT due to muon aligment mismodelling.
alignementcorrswitch = False
if "AlignmentCorr" in options.dir:
	alignementcorrswitch = True

print 'EMu Switch = ', emuswitch
print 'NonIso Switch = ', nonisoswitch
print 'Quick Switch (No Sys) = ', quicktestswitch
print 'AlignmentCorr Switch = ', alignementcorrswitch


# Typical event weight, sigma*lumi/Ngenerated
startingweight = float(options.crosssection)*float(options.lumi)/float(options.ntotal)

# Get the file, tree, and number of entries
print name

fin = TFile.Open(name,"READ")
to = fin.Get("rootTupleTree/tree")
No = to.GetEntries()

# Here we are going to pre-skim the file to reduce running time.
indicator = ((name.split('_'))[-1]).replace('.root','')

junkfile1 = str(randint(100000000,1000000000))+indicator+'junk.root'

# At least one 100 GeV PFJet
fj1 = TFile.Open(junkfile1,'RECREATE')
t1 = to.CopyTree('PFJetPt[]>110')
# t1 = to.CopyTree('(1)')
Nj1 = t1.GetEntries()

junkfile2 = str(randint(100000000,1000000000))+indicator+'junk.root'

# At least one 40 GeV muon
fj2 = TFile.Open(junkfile2,'RECREATE')
t = t1.CopyTree('MuonPt[]>42')
N = t.GetEntries()

# PRint the reduction status
print 'Original events:          ',No
print 'After demand 1 pT110 jet: ',Nj1
print 'After demand 1 pt42 muon: ',N

##########################################################################################
#################      PREPARE THE VARIABLES FOR THE OUTPUT TREE   #######################
##########################################################################################

# Branches will be created as follows: One branch for each kinematic variable for each 
# systematic variation determined in _variations. One branch for each weight and flag.
# So branch names will include weight_central, run_number, Pt_muon1, Pt_muon1MESUP, etc.

_kinematicvariables = ['Pt_muon1','Pt_muon2','Pt_ele1','Pt_ele2','Pt_jet1','Pt_jet2','Pt_miss']
_kinematicvariables += ['Eta_muon1','Eta_muon2','Eta_ele1','Eta_ele2','Eta_jet1','Eta_jet2','Eta_miss']
_kinematicvariables += ['Phi_muon1','Phi_muon2','Phi_ele1','Phi_ele2','Phi_jet1','Phi_jet2','Phi_miss']
_kinematicvariables += ['TrkIso_muon1','TrkIso_muon2']
_kinematicvariables += ['Chi2_muon1','Chi2_muon2']
_kinematicvariables += ['PFID_muon1','PFID_muon2']
_kinematicvariables += ['TrkMeasLayers_muon1','TrkMeasLayers_muon2']
_kinematicvariables += ['Charge_muon1','Charge_muon2']
_kinematicvariables += ['TrkGlbDpt_muon1','TrkGlbDpt_muon2']
_kinematicvariables += ['NHEF_jet1','NHEF_jet2','NEMEF_jet1','NEMEF_jet2']
_kinematicvariables += ['St_uujj','St_uvjj']
_kinematicvariables += ['St_eejj','St_evjj']
_kinematicvariables += ['M_uu','MT_uv']
_kinematicvariables += ['DR_muon1muon2','DPhi_muon1met','DPhi_jet1met','DPhi_jet2met']
_kinematicvariables += ['DR_muon1jet1','DR_muon1jet2','DR_muon2jet1','DR_muon2jet2']
_kinematicvariables += ['DPhi_muon1jet1','DPhi_muon1jet2','DPhi_muon2jet1','DPhi_muon2jet2']
_kinematicvariables += ['M_uujj1','M_uujj2','M_uujjavg','MT_uvjj1','MT_uvjj2','M_uvjj','MT_uvjj']
_kinematicvariables += ['MH_uujj','MH_uvjj']
_kinematicvariables += ['M_eejj1','M_eejj2','MT_evjj1','MT_evjj2','M_evjj','MT_evjj']
_kinematicvariables += ['JetCount','MuonCount','ElectronCount','GenJetCount']
_kinematicvariables += ['IsMuon_muon1','IsMuon_muon2']
_weights = ['weight_nopu','weight_central', 'weight_pu_up', 'weight_pu_down','weight_central_2012D']
_flags = ['run_number','event_number','lumi_number','pass_HLTMu40_eta2p1','GoodVertexCount']
_flags += ['passPrimaryVertex','passBeamScraping','passHBHENoiseFilter','passBPTX0','passBeamHalo','passTrackingFailure','passTriggerObjectMatching','passDataCert']
_flags += ['passBadEESuperCrystal','passEcalDeadCellBE','passEcalDeadCellTP','passEcalLaserCorr','passHcalLaserEvent','passPhysDeclared']
_variations = ['','JESup','JESdown','MESup','MESdown','JERup','JERdown','MER']
# _variations = ['','JESup','JESdown','MESup','MESdown','EESup','EESdown','JER','MER','EER']
if nonisoswitch==True or emuswitch==True or quicktestswitch==True:
	print 'NOT performing systematics...'
	_variations = ['']  # For quicker tests
# _variations = ['']  # For quicker tests



##########################################################################################
#################     Everything needed for Pileup reweighting     #######################
##########################################################################################



def GetPURescalingFactors(puversion):
	# Purpose: To get the pileup reweight factors from the PU_Central.root, PU_Up.root, and PU_Down.root files.
	#         The MC Truth distribution is taken from https://twiki.cern.ch/twiki/bin/view/CMS/PileupMCReweightingUtilities

	MCDistSummer12 = [2.560E-06, 5.239E-06, 1.420E-05, 5.005E-05, 1.001E-04, 2.705E-04, 1.999E-03, 6.097E-03, 1.046E-02, 1.383E-02, 
                      1.685E-02, 2.055E-02, 2.572E-02, 3.262E-02, 4.121E-02, 4.977E-02, 5.539E-02, 5.725E-02, 5.607E-02, 5.312E-02, 5.008E-02, 4.763E-02, 
                      4.558E-02, 4.363E-02, 4.159E-02, 3.933E-02, 3.681E-02, 3.406E-02, 3.116E-02, 2.818E-02, 2.519E-02, 2.226E-02, 1.946E-02, 1.682E-02, 
                      1.437E-02, 1.215E-02, 1.016E-02, 8.400E-03, 6.873E-03, 5.564E-03, 4.457E-03, 3.533E-03, 2.772E-03, 2.154E-03, 1.656E-03, 1.261E-03, 
                      9.513E-04, 7.107E-04, 5.259E-04, 3.856E-04, 2.801E-04, 2.017E-04, 1.439E-04, 1.017E-04, 7.126E-05, 4.948E-05, 3.405E-05, 2.322E-05, 
                      1.570E-05, 5.005E-06]

    # This is the standard (all of 2012) pileup scenario
	if puversion =='Basic':
		h_pu_up = TFile.Open("PU_Up.root",'read').Get('pileup')
		h_pu_down = TFile.Open("PU_Down.root",'read').Get('pileup')
		h_pu_central = TFile.Open("PU_Central.root",'read').Get('pileup')

	# This is just for 2012D. It was used for some studies. Not that important.
	if puversion =='2012D':
		h_pu_up = TFile.Open("PU_Up_2012D.root",'read').Get('pileup')
		h_pu_down = TFile.Open("PU_Down_2012D.root",'read').Get('pileup')
		h_pu_central = TFile.Open("PU_Central_2012D.root",'read').Get('pileup')

	# Arrays for the central and up/down variation weights.
	bins_pu_central = []
	bins_pu_up = []
	bins_pu_down = []

	# Loop over bins and put content in arrays
	for x in range(h_pu_up.GetNbinsX()):
		bin = x +1
		bins_pu_central.append(h_pu_central.GetBinContent(bin))
		bins_pu_up.append(h_pu_up.GetBinContent(bin))
		bins_pu_down.append(h_pu_down.GetBinContent(bin))

	# Sum bins for proper normalizations
	total_pu_central = sum(bins_pu_central)
	total_pu_up = sum(bins_pu_up)
	total_pu_down = sum(bins_pu_down)
	total_mc = sum(MCDistSummer12)

	# Get normalized bins
	bins_pu_central_norm = [x/total_pu_central for x in bins_pu_central]
	bins_pu_up_norm = [x/total_pu_up for x in bins_pu_up]
	bins_pu_down_norm = [x/total_pu_down for x in bins_pu_down]
	bins_mc_norm  = [x/total_mc for x in MCDistSummer12]

	# Arrays for scale factors (central and systematic varied)
	scale_pu_central = []
	scale_pu_up = []
	scale_pu_down = []

	# Fill arrays of scale factors
	for x in range(len(bins_mc_norm)):
		scale_pu_central.append(bins_pu_central_norm[x]/bins_mc_norm[x])
		scale_pu_up.append(bins_pu_up_norm[x]/bins_mc_norm[x])
		scale_pu_down.append(bins_pu_down_norm[x]/bins_mc_norm[x])

	# Return arrays of scale factors
	return [scale_pu_central, scale_pu_up, scale_pu_down]

# Use the above function to get the pu weights
[CentralWeights,UpperWeights,LowerWeights] =GetPURescalingFactors('Basic')
[CentralWeights_2012D,UpperWeights_2012D,LowerWeights_2012D] =GetPURescalingFactors('2012D')




##########################################################################################
#################     Everything needed for PDF Weight variation   #######################
##########################################################################################



def GetPDFWeightVars(T):
	# Purpose: Determine all the branch names needed to store the PDFWeights 
	#         for CTEQ, MSTW, and NNPDF in flat (non vector) form. 
	if T.isData:
		return []
	else:
		T.GetEntry(1)
		pdfweights=[]
		for x in range(len(T.PDFCTEQWeights)):
			pdfweights.append('factor_cteq_'+str(x+1))
		for x in range(len(T.PDFMSTWWeights)):
			pdfweights.append('factor_mstw_'+str(x+1))		
		for x in range(len(T.PDFNNPDFWeights)):
			pdfweights.append('factor_nnpdf_'+str(x+1))			
		return pdfweights


# Get the appropriate numbers of PDF weights from the tree
_pdfweightsnames = GetPDFWeightVars(t)

##########################################################################################
#################         Prepare the Output Tree                  #######################
##########################################################################################

# First create the output file. 
tmpfout = str(randint(100000000,1000000000))+indicator+'.root'
finalfout = options.dir+'/'+(name.split('/')[-2]+'__'+name.split('/')[-1].replace('.root','_tree.root'))

# Create the output file and tree "PhysicalVariables"
fout = TFile.Open(tmpfout,"RECREATE")
tout=TTree("PhysicalVariables","PhysicalVariables")


# Below all the branches are created, everything is a double except for flags
# for b in _kinematicvariables:
# 	for v in _variations:
# 		exec(b+v+' = array.array("f",[0])')
# 		exec('tout.Branch("'+b+v+'",'+b+v+',"'+b+v+'/F")' )
# for b in _weights:
# 	exec(b+' = array.array("f",[0])')
# 	exec('tout.Branch("'+b+'",'+b+',"'+b+'/F")' )
# if dopdf:
# 	for b in _pdfweights:
# 		exec(b+' = array.array("f",[0])')
# 		print (b+' = array.array("f",[0])')
# 		exec('tout.Branch("'+b+'",'+b+',"'+b+'/F")' )
# for b in _flags:
# 	exec(b+' = array.array("L",[0])')
# 	exec('tout.Branch("'+b+'",'+b+',"'+b+'/i")' )

Branches = {}
for b in _kinematicvariables:
	for v in _variations:
		Branches[b+v] = array.array("f",[0])
		tout.Branch(b+v,Branches[b+v],b+v+"/F")
for b in _weights:
	Branches[b] = array.array("f",[0])
	tout.Branch(b,Branches[b],b+"/F")
if dopdf:
	for b in _pdfweightsnames:
		Branches[b] = array.array("f",[0])
		tout.Branch(b,Branches[b],b+"/F")
for b in _flags:
	Branches[b] = array.array("L",[0])
	tout.Branch(b,Branches[b],b+"/i")


##########################################################################################
#################           SPECIAL FUNCTIONS FOR ANALYSIS         #######################
##########################################################################################

def PrintBranchesAndExit(T):
	# Purpose: Just list the branches on the input file and bail out. 
	#         For coding and debugging
	x = T.GetListOfBranches()
	for n in x:
		print n
	sys.exit()

# PrintBranchesAndExit(t)

def GetRunLumiList():
	# Purpose: Parse the json file to get a list of good runs and lumis 
	#          to call on later. For real data only.
	jfile = open(options.json,'r')	
	flatjson = ''
	for line in jfile:
		flatjson+=line.replace('\n','')
	flatjson = flatjson.replace("}","")
	flatjson = flatjson.replace("{","")
	flatjson = flatjson.replace(":","")
	flatjson = flatjson.replace(" ","")
	flatjson = flatjson.replace("\t","")

	jinfo = flatjson.split('"')
	strjson = ''
	for j in jinfo:
		strjson += j
	strjson = strjson.replace('\n[',' [')
	strjson = strjson.replace(']],',']]\n')
	strjson = strjson.replace('[[',' [[')

	pairs = []
	for line in strjson.split('\n'):
		pair = []
		line = line.split(' ')
		exec('arun = '+line[0])
		exec('alumis = '+line[1])
		verboselumis = []
		for r in alumis:
			verboselumis +=  range(r[0],r[1]+1)

		pair.append(arun)
		pair.append(verboselumis)
		pairs.append(pair)
	return pairs

GoodRunLumis = GetRunLumiList()

def CheckRunLumiCert(r,l):
	# Purpose: Use the GoodRunLumis list, to check and see if a given
	#          run and lumi (r and l) are in the list. 
	for _rl in GoodRunLumis:
		if _rl[0]==r:
			for _l in _rl[1]:
				if _l == l:
					return True
	return False


def GeomFilterCollection(collection_to_clean,good_collection,dRcut):
	# Purpose: Take a collection of TLorentzVectors that you want to clean (arg 1)
	#         by removing all objects within dR of dRcut (arg 3) of any element in
	#         the collection of other particles (arg 2)
	#         e.g.  argumments (jets,muons,0.3) gets rid of jets within 0.3 of muons. 
	output_collection = []
	for c in collection_to_clean:
		isgood = True
		for g in good_collection:
			if (c.DeltaR(g))<dRcut:
				isgood = False
		if isgood==True:
			output_collection.append(c)
	return output_collection

def TransMass(p1,p2):
	# Purpose: Simple calculation of transverse mass between two TLorentzVectors
	return math.sqrt( 2*p1.Pt()*p2.Pt()*(1-math.cos(p1.DeltaPhi(p2))) )

def InvMass(particles):
	# Purpose: Simple calculation of invariant mass between two TLorentzVectors	
	output=particles
	return (p1+p2).M()

def ST(particles):
	# Purpose: Calculation of the scalar sum of PT of a set of TLorentzVectors	
	st = 0.0
	for p in particles:
		st += p.Pt()
	return st

def PassTrigger(T,trigger_identifiers,prescale_threshold):
	# Purpose: Return a flag (1 or 0) to indicate whether the event passes any trigger
	#         which is syntactically matched to a set of strings trigger_identifiers,
	#         considering only triggers with a prescale <= the prescale threshold.	
	for n in range(len(T.HLTInsideDatasetTriggerNames)):
		name = T.HLTInsideDatasetTriggerNames[n]
		consider_trigger=True

		for ident in trigger_identifiers:
			if ident not in name:
				consider_trigger=False
		if (consider_trigger==False) : continue

		prescale = T.HLTInsideDatasetTriggerPrescales[n]
		if prescale > prescale_threshold:
			consider_trigger=False
		if (consider_trigger==False) : continue

		decision = T.HLTInsideDatasetTriggerDecisions[n]
		if decision==True:
			return 1
	return 0	

def CountVertices(T):
	vertices = 0
	for v in range(len(T.VertexZ)):
		if ( T.VertexIsFake[v] == True ) :  continue
		if ( T.VertexNDF[v] <= 4.0 ) :  continue
		if ( abs(T.VertexZ[v]) > 24.0 ) :  continue
		if ( abs(T.VertexRho[v]) >= 2.0 ) :  continue
		vertices += 1
	return vertices	

def GetPUWeight(T,version,puversion):
	# Purpose: Get the pileup weight for an event. Version can indicate the central
	#         weight, or the Upper or Lower systematics. Needs to be updated for
	#         input PU histograms given only the generated disribution........	

	# Only necessary for MC
	if T.isData:
		return 1.0

	# Getting number of PU interactions, start with zero.	
	N_pu = 0

	# Set N_pu to number of true PU interactions in the central bunch
	for n in range(len(T.PileUpInteractionsTrue)):
		if abs(T.PileUpOriginBX[n]==0):
			N_pu = int(1.0*(T.PileUpInteractionsTrue[n]))

	puweight = 0

	# Assign the list of possible PU weights according to what is being done
	# Central systematics Up, or systematic down
	if puversion=='Basic':
		puweights = CentralWeights
		if version=='SysUp':
			puweights=UpperWeights
		if version=='SysDown':
			puweights=LowerWeights

	# Also possible to do just for 2012D, for cross-checks. 
	if puversion=='2012D':
		puweights = CentralWeights_2012D
		if version=='SysUp':
			puweights=UpperWeights_2012D
		if version=='SysDown':
			puweights=LowerWeights_2012D


	# Make sure there exists a weight for the number of interactions given, 
	# and set the puweight to the appropriate value.
	NRange = range(len(puweights))
	if N_pu in NRange:
		puweight=puweights[N_pu]
	# print puweight
	return puweight


def GetPDFWeights(T):
	# Purpose: Gather the pdf weights into a single list. 	
	_allweights = []
	_allweights += T.PDFCTEQWeights
	_allweights += T.PDFNNPDFWeights
	_allweights += T.PDFMSTWWeights
	return _allweights


def MuonsFromLQ(T):
	# Purpose: Testing. Get the muons from LQ decays and find the matching reco muons. 
	#         Return TLorentzVectors of the gen and reco muons, and the indices for
	#         the recomuons as well.
	muons = []
	genmuons=[]
	recomuoninds = []
	for n in range(len(T.MuonPt)):	
		m = TLorentzVector()
		m.SetPtEtaPhiM(T.MuonPt[n],T.MuonEta[n],T.MuonPhi[n],0)
		muons.append(m)
	for n in range(len(T.GenParticlePdgId)):
		pdg = T.GenParticlePdgId[n]
		if pdg not in [13,-13]:
			continue
		motherIndex = T.GenParticleMotherIndex[n]
		motherid = 0
		if motherIndex>-1:
			motherid = T.GenParticlePdgId[motherIndex]
		if motherid not in [42,-42]:
			continue	
		m = TLorentzVector()
		m.SetPtEtaPhiM(T.GenParticlePt[n],T.GenParticleEta[n],T.GenParticlePhi[n],0.0)
		genmuons.append(m)
	
	matchedrecomuons=[]
	emptyvector = TLorentzVector()
	emptyvector.SetPtEtaPhiM(0,0,0,0)
	for g in genmuons:
		bestrecomuonind=-1
		mindr = 99999
		ind=-1
		for m in muons:
			ind+=1
			dr = abs(m.DeltaR(g))
			if dr<mindr:
				mindr =dr
				bestrecomuonind=ind
		if mindr<0.4:
			matchedrecomuons.append(muons[bestrecomuonind])
			recomuoninds.append(bestrecomuonind)
		else:
			matchedrecomuons.append(emptyvector)
			recomuoninds.append(-99)
		# print mindr, muons[bestrecomuonind].Pt(), g.Pt()
	return([genmuons,matchedrecomuons,recomuoninds])


def PropagatePTChangeToMET(met,original_object,varied_object):
	# Purpose: This takes an input TLorentzVector met representing the missing ET
	#         (no eta component), and an original object (arg 2), which has been
	#         kinmatically modified for a systematic (arg 3), and modifies the 
	#         met to compensate for the change in the object.
	return  met + varied_object - original_object




def TightHighPtIDMuons(T,_met,variation,isdata):
	# Purpose: Gets the collection of muons passing tight muon ID. 
	#         Returns muons as TLorentzVectors, and indices corrresponding
	#         to the surviving muons of the muon collection. 
	#         Also returns modified MET for systematic variations.
	muons = []
	muoninds = []
	if variation=='MESup':	
		_MuonCocktailPt = [(pt + pt*(0.05*pt/1000.0)) for pt in T.MuonCocktailPt]
	elif variation=='MESdown':	
		_MuonCocktailPt = [(pt - pt*(0.05*pt/1000.0)) for pt in T.MuonCocktailPt]
	elif variation=='MER':	
		_MuonCocktailPt = [pt+pt*tRand.Gaus(0.0,  0.01*(pt<=200.0) + (0.04)*(pt>200.0) ) for pt in T.MuonCocktailPt]
	else:	
		_MuonCocktailPt = [pt for pt in T.MuonCocktailPt]	

	if (isdata):
		_MuonCocktailPt = [pt for pt in T.MuonCocktailPt]	

	trk_isos = []
	charges = []
	deltainvpts = []

	chi2 = []
	pfid = []
	layers = []

	# Loop over muons using the pT array from above
	for n in range(len(_MuonCocktailPt)):

		# Some muon alignment studies use the inverse diff of the high pT and Trk pT values
		deltainvpt = -1.0	
		if ( T.MuonTrkPt[n] > 0.0 ) and (_MuonCocktailPt[n]>0.0):
			deltainvpt = ( 1.0/T.MuonTrkPt[n] - 1.0/_MuonCocktailPt[n])
	
		# For alignment correction studies in MC, the pT is modified according to
		# parameterizations of the position
		if alignementcorrswitch == True and isdata==False:
			if abs(deltainvpt) > 0.0000001:
				__Pt_mu = _MuonCocktailPt[n]
				__Eta_mu = T.MuonCocktailEta[n]
				__Phi_mu = T.MuonCocktailPhi[n]
				__Charge_mu = T.MuonCharge[n]
				if (__Pt_mu >200)*(abs(__Eta_mu) < 0.9)      : 
					_MuonCocktailPt[n] =  ( (1.0) / ( -5e-05*__Charge_mu*sin(-1.4514813+__Phi_mu ) + 1.0/__Pt_mu ) ) 
				deltainvpt = ( 1.0/T.MuonTrkPt[n] - 1.0/_MuonCocktailPt[n])


		# For the ID, begin by assuming it passes. Veto if it fails any condition
		# High PT conditions from https://twiki.cern.ch/twiki/bin/view/CMSPublic/SWGuideMuonId
		# NTuple definitions in https://raw.githubusercontent.com/CMSLQ/RootTupleMakerV2/master/src/RootTupleMakerV2_Muons.cc
		Pass = True
		# A preliminary pT cut. This also encompasses the GlobalMuon conditions, since
		# all non-global muosn have cocktail pT of -1 in the ntuples.
		Pass *= (_MuonCocktailPt[n] > 35)      
		# Eta requirement matches trigger.
		Pass *= abs(T.MuonCocktailEta[n])<2.1    

		# Number of valid hits
		Pass *= T.MuonGlobalTrkValidHits[n]>=1

		# Number of station matches
		Pass *= T.MuonStationMatches[n]>1 

		# Impact parameters
		Pass *= abs(T.MuonCocktailTrkVtxDXY[n]) < 0.2     
		Pass *= abs(T.MuonCocktailTrkVtxDZ[n]) < 0.5      

		# Pixel hits
		Pass *= T.MuonTrkPixelHits[n]>=1  

		# Layers with measurement (high PT ID cut is 5, used to be tight id cut at 8)
		Pass *= T.MuonTrackLayersWithMeasurement[n] > 5 


		# Isolation condition now using delta beta isolation
		# if nonisoswitch != True:
		# 	sumChargedHadronPt = T.MuonPFIsoR04ChargedHadron[n]
		# 	sumNeutralHadronPt = T.MuonPFIsoR04NeutralHadron[n]
		# 	sumPhotonPt        = T.MuonPFIsoR04Photon[n]
		# 	sumPUPt            = T.MuonPFIsoR04PU
		# 	muonisolotion = sumChargedHadronPt+ max([0.,sumNeutralHadronPt+sumPhotonPt-0.5*sumPUPt])
		# 	Pass*= (muonisolotion)/(T.MuonCocktailPt[n]) < 0.12
		# 	Pass *= (T.MuonTrackerIsoSumPT[nequiv[n]]/_MuonCocktailPt[n])<0.1

		# Isolation condition using tracker-only isolation
		if nonisoswitch != True:
			Pass *= (T.MuonTrackerIsoSumPT[n]/_MuonCocktailPt[n])<0.1

		# Propagate MET changes if undergoing systematic variation
		if (Pass):
			NewMu = TLorentzVector()
			OldMu = TLorentzVector()
			NewMu.SetPtEtaPhiM(_MuonCocktailPt[n],T.MuonCocktailEta[n],T.MuonCocktailPhi[n],0)
			OldMu.SetPtEtaPhiM(T.MuonCocktailPt[n],T.MuonCocktailEta[n],T.MuonCocktailPhi[n],0)
			_met = PropagatePTChangeToMET(_met,OldMu,NewMu)

		# Append items to retun if the muon is good
		if (Pass):
			muons.append(NewMu)
			trk_isos.append((T.MuonTrackerIsoSumPT[n]/_MuonCocktailPt[n]))
			chi2.append(T.MuonGlobalChi2[n])
			pfid.append(T.MuonIsPF[n])
			layers.append(T.MuonTrackLayersWithMeasurement[n])
			charges.append(T.MuonCocktailCharge[n])
			muoninds.append(n)
			deltainvpts.append(deltainvpt)

	return [muons,muoninds,_met,trk_isos,charges,deltainvpts,chi2,pfid,layers]


def HEEPElectrons(T,_met,variation):
	# Purpose: Gets the collection of electrons passing HEEP ID. 
	#         Returns electrons as TLorentzVectors, and indices corrresponding
	#         to the surviving electrons of the electron collection. 
	#         Also returns modified MET for systematic variations.	
	electrons = []
	electroninds = []
	if variation=='EESup':	
		_ElectronPt = [pt*1.01 for pt in T.ElectronPtHeep]
	elif variation=='EESdown':	
		_ElectronPt = [pt*0.99 for pt in T.ElectronPtHeep]
	elif variation=='EER':	
		_ElectronPt = [pt+pt*tRand.Gaus(0.0,0.04) for pt in T.ElectronPtHeep]
	else:	
		_ElectronPt = [pt for pt in T.ElectronPtHeep]	

	for n in range(len(_ElectronPt)):
		Pass = True
		Pass *= (T.ElectronPtHeep[n] > 35)
		Pass *= abs(T.ElectronEta[n])<2.1

		barrel = (abs(T.ElectronEta[n]))<1.442
		endcap = (abs(T.ElectronEta[n]))>1.56 
		Pass *= (barrel+endcap)

		if barrel:
			Pass *= T.ElectronHasEcalDrivenSeed[n]
			Pass *= T.ElectronDeltaEtaTrkSC[n] < 0.005
			Pass *= T.ElectronDeltaPhiTrkSC[n] < 0.06
			Pass *= T.ElectronHoE[n] < 0.05
			Pass *= ((T.ElectronE2x5OverE5x5[n] > 0.94) or (T.ElectronE1x5OverE5x5[n] > 0.83) )
			Pass *= T.ElectronHcalIsoD1DR03[n] <  (2.0 + 0.03*_ElectronPt[n] + 0.28*T.rhoForHEEP)
			Pass *= T.ElectronTrkIsoDR03[n] < 5.0
			Pass *= T.ElectronMissingHits[n] <=1
			Pass *= T.ElectronLeadVtxDistXY[n]<0.02

		if endcap:
			Pass *= T.ElectronHasEcalDrivenSeed[n]
			Pass *= T.ElectronDeltaEtaTrkSC[n] < 0.007
			Pass *= T.ElectronDeltaPhiTrkSC[n] < 0.06
			Pass *= T.ElectronHoE[n] < 0.05
			Pass *= T.ElectronSigmaIEtaIEta[n] < 0.03
			if _ElectronPt[n]<50:
				Pass *= (T.ElectronHcalIsoD1DR03[n] < (2.5 + 0.28*T.rhoForHEEP))
			else:
				Pass *= (T.ElectronHcalIsoD1DR03[n] < (2.5 + 0.03*(_ElectronPt[n]-50.0) + 0.28*T.rhoForHEEP))
			Pass *= T.ElectronTrkIsoDR03[n] < 5.0
			Pass *= T.ElectronMissingHits[n] <=1
			Pass *= T.ElectronLeadVtxDistXY[n]<0.05

		if (Pass):
			NewEl = TLorentzVector()
			OldEl = TLorentzVector()
			NewEl.SetPtEtaPhiM(_ElectronPt[n],T.ElectronEta[n],T.ElectronPhi[n],0)
			OldEl.SetPtEtaPhiM(T.ElectronPtHeep[n],T.ElectronEta[n],T.ElectronPhi[n],0)
			met = PropagatePTChangeToMET(_met,OldEl,NewEl)

		Pass *= (_ElectronPt[n] > 35)
		if (Pass):
			electrons.append(NewEl)
			electroninds.append(n)
	return [electrons,electroninds,_met]

def LooseIDJets(T,_met,variation,isdata):
	# Purpose: Gets the collection of jets passing loose PFJet ID. 
	#         Returns jets as TLorentzVectors, and indices corrresponding
	#         to the surviving jetss of the jet collection. 
	#         Also returns modified MET for systematic variations.	

	# Switch ntuple branches depending on systematic variation
	if ("JE" not in variation) or isdata==True:
		_PFJetPt = [pt for pt in T.PFJetPt]
	else:
		if variation == 'JERup':
			_PFJetPt = [pt for pt in T.PFJetSmearedUpPt]
			_met.SetPtEtaPhiM(T.PFMETType01XYCorJetResUp[0],0,T.PFMETPhiType01XYCorJetResUp[0],0)
		if variation == 'JERdown':
			_PFJetPt = [pt for pt in T.PFJetSmearedDownPt]
			_met.SetPtEtaPhiM(T.PFMETType01XYCorJetResDown[0],0,T.PFMETPhiType01XYCorJetResDown[0],0)

		if variation == 'JESup':
			_PFJetPt = [pt for pt in T.PFJetScaledUpPt]
			_met.SetPtEtaPhiM(T.PFMETType01XYCorJetEnUp[0],0,T.PFMETPhiType01XYCorJetEnUp[0],0)

		if variation == 'JESdown':
			_PFJetPt = [pt for pt in T.PFJetScaledDownPt]
			_met.SetPtEtaPhiM(T.PFMETType01XYCorJetEnDown[0],0,T.PFMETPhiType01XYCorJetEnDown[0],0)

	# This is just a variable which will store the highest pT jet failing ID
	# It was just a curiosity.
	JetFailThreshold=0.0

	# The list of jets, their indices in the jet list, and a couple energy fractions
	# we were interested in storing.
	jets=[]
	jetinds = []
	NHF = []
	NEMF = []

	# Loop over jets
	for n in range(len(_PFJetPt)):
		#  Jet kinematics thresholds. More pT cuts will be applied later.
		if _PFJetPt[n]>30 and abs(T.PFJetEta[n])<2.4 :
			# ID criteria
			if T.PFJetPassLooseID[n]==1:
				j = TLorentzVector()
				j.SetPtEtaPhiM(_PFJetPt[n],T.PFJetEta[n],T.PFJetPhi[n],0)		
				jets.append(j)
				jetinds.append(n)
				NHF.append(T.PFJetNeutralHadronEnergyFraction[n])
				NEMF.append(T.PFJetNeutralEmEnergyFraction[n])
			else:
				if _PFJetPt[n] > JetFailThreshold:
					JetFailThreshold = _PFJetPt[n]

	return [jets,jetinds,_met,JetFailThreshold,NHF,NEMF]

def MetVector(T):
	# Purpose: Creates a TLorentzVector represting the MET. No pseudorapidith, obviously.
	met = TLorentzVector()
	met.SetPtEtaPhiM(T.PFMETType01XYCor[0],0,T.PFMETPhiType01XYCor[0],0)
	return met

def GetLLJJMasses(l1,l2,j1,j2):
	# Purpose: For LLJJ channels, this function returns two L-J Masses, corresponding to the
	#         pair of L-Js which minimizes the difference between LQ masses in the event

	# These are the invariant mass combinations 
	m11 = (l1+j1).M()
	m12 = (l1+j2).M()
	m21 = (l2+j1).M()
	m22 = (l2+j2).M()
	mh = 0.0 # This will be the invariant mass of the lepton and leading jet

	# Difference in Mass for the two matching scenarios
	diff1 = abs(m21-m12)
	diff2 = abs(m11-m22)

	# The ideal match minimizes the Mass difference above
	# Based on the the diffs, store the appropriate pairs	
	if diff1 < diff2:
		pair =  [m21,m12] # The invariant mass pair
		mh = m21          # invariant mass corresponding to leading jet
	else:
		pair = [m11,m22]  # The invariant mass pair
		mh = m11          # invariant mass corresponding to leading jet
	pair.sort()
	pair.reverse()
	pair.append(mh)
	return pair

def GetLVJJMasses(l1,met,j1,j2):
	# Purpose: For LVJJ channels, this function returns two L-J Masses, and an LJ mass and mT, 
	#         Quantities corresponding to the pair of L-Js which minimizes the difference 
	#         between LQ masses in the event

	# These are the lepton-jet masses
	m11 = (l1+j1).M()
	m12 = (l1+j2).M()
	# These are the lepton-jet transverse masses
	mt11 = TransMass(l1,j1)
	mt12 = TransMass(l1,j2)
	# These are the met-jet transverse masses
	mte1 = TransMass(met,j1)
	mte2 = TransMass(met,j2)
	mh = 0.0	
	# Difference in MT for the two matching scenarios
	diff1 = abs(mte1-mt12)  # MET matched to jet1, lepton matched to jet2
	diff2 = abs(mt11-mte2)  # MET matched to jet2, lepton matched to jet1
	# The ideal match minimizes the MT difference above
	# Based on the the diffs, store the appropriate pairs
	if diff1 < diff2:
		pair =  [mte1,mt12]      # These are the two trans-mass values
		pairwithinv = [m12,mte1] # Instead we could store one invariant mass and one trans mass
	# This is the other matching possibility
	else:
		pair = [mt11,mte2]
		invmass = m11
		mh = m11 # The invariant mass pair with the leading jet
		pairwithinv = [m11,mte2]
	# Let put the pair of trans-masses in pT order
	pair.sort()
	pair.reverse()
	
	return [pair,pairwithinv,mh]


##########################################################################################
###########      FULL CALCULATION OF ALL VARIABLES, REPEATED FOR EACH SYS   ##############
##########################################################################################

def FullKinematicCalculation(T,variation):
	# Purpose: This is the magic function which calculates all kinmatic quantities using
	#         the previous functions. It returns them as a simple list of doubles. 
	#         It will be used in the loop over events. The 'variation' argument is passed
	#         along when getting the sets of leptons and jets, so the kinematics will vary.
	#         This function is repeated for all the sytematic variations inside the event
	#         loop. The return arguments ABSOLUELY MUST be in the same order they are 
	#         listed in the branch declarations. Modify with caution.  

	# MET as a vector
	met = MetVector(T)
	# ID Muons,Electrons
	[muons,goodmuoninds,met,trkisos,charges,dpts,chi2,pfid,layers] = TightHighPtIDMuons(T,met,variation,T.isData)
	[electrons,electroninds,met] = HEEPElectrons(T,met,variation)
	# ID Jets and filter from muons
	[jets,jetinds,met,failthreshold,neutralhadronEF,neutralemEF] = LooseIDJets(T,met,variation,T.isData)
	jets = GeomFilterCollection(jets,muons,0.3)
	jets = GeomFilterCollection(jets,electrons,0.3)
	# Empty lorenz vector for bookkeeping
	EmptyLorentz = TLorentzVector()
	EmptyLorentz.SetPtEtaPhiM(.01,0,0,0)

	# Muon and Jet Counts
	_mucount = len(muons)
	_elcount = len(electrons)
	_jetcount = len(jets)

	# Make sure there are two of every object, even if zero
	if len(muons) < 1 : 
		muons.append(EmptyLorentz)
		trkisos.append(0.0)
		charges.append(0.0)
		dpts.append(-1.0)
		chi2.append(-1.0)
		pfid.append(-1.0)
		layers.append(-1.0)

	if len(muons) < 2 : 
		muons.append(EmptyLorentz)
		trkisos.append(0.0)
		charges.append(0.0)		
		dpts.append(-1.0)
		chi2.append(-1.0)
		pfid.append(-1.0)
		layers.append(-1.0)

	if len(electrons) < 1 : electrons.append(EmptyLorentz)
	if len(electrons) < 2 : electrons.append(EmptyLorentz)	
	if len(jets) < 1 : 
		jets.append(EmptyLorentz)
		neutralhadronEF.append(0.0)
		neutralemEF.append(0.0)
	if len(jets) < 2 : 
		jets.append(EmptyLorentz)
		neutralhadronEF.append(0.0)
		neutralemEF.append(0.0)		

	_ismuon_muon1 = 1.0
	_ismuon_muon2 = 1.0

	if emuswitch == True:
		if muons[0].Pt() > electrons[0].Pt():
			muons[1] = electrons[0]
			_ismuon_muon2 = 0.0
		else:
			muons[1] = muons[0]
			muons[0] = electrons[0]
			_ismuon_muon1=0.0

	# Get kinmetic quantities
	[_ptmu1,_etamu1,_phimu1,_isomu1,_qmu1,_dptmu1] = [muons[0].Pt(),muons[0].Eta(),muons[0].Phi(),trkisos[0],charges[0],dpts[0]]
	[_ptmu2,_etamu2,_phimu2,_isomu2,_qmu2,_dptmu2] = [muons[1].Pt(),muons[1].Eta(),muons[1].Phi(),trkisos[1],charges[1],dpts[1]]

	[_chimu1,_chimu2] = [chi2[0],chi2[1]]
	[_ispfmu1,ispfmu2] = [pfid[0],pfid[1]]
	[_layersmu1,_layersmu2] = [layers[0],layers[1]]

	[_ptel1,_etael1,_phiel1] = [electrons[0].Pt(),electrons[0].Eta(),electrons[0].Phi()]
	[_ptel2,_etael2,_phiel2] = [electrons[1].Pt(),electrons[1].Eta(),electrons[1].Phi()]
	[_ptj1,_etaj1,_phij1]    = [jets[0].Pt(),jets[0].Eta(),jets[0].Phi()]
	[_ptj2,_etaj2,_phij2]    = [jets[1].Pt(),jets[1].Eta(),jets[1].Phi()]
	[_nhefj1,_nhefj2,_nemefj1,_nemefj2] = [neutralhadronEF[0],neutralhadronEF[1],neutralemEF[0],neutralemEF [1]]
	[_ptmet,_etamet,_phimet] = [met.Pt(),0,met.Phi()]

	_stuujj = ST([muons[0],muons[1],jets[0],jets[1]])
	_stuvjj = ST([muons[0],met,jets[0],jets[1]])

	_steejj = ST([electrons[0],electrons[1],jets[0],jets[1]])
	_stevjj = ST([electrons[0],met,jets[0],jets[1]])


	_Muu = (muons[0]+muons[1]).M()
	_MTuv = TransMass(muons[0],met)
	_DRuu = (muons[0]).DeltaR(muons[1])
	_DPHIuv = abs((muons[0]).DeltaPhi(met))
	_DPHIj1v = abs((jets[0]).DeltaPhi(met))
	_DPHIj2v = abs((jets[1]).DeltaPhi(met))

	_DRu1j1 = abs(muons[0].DeltaR(jets[0]))
	_DRu1j2 = abs(muons[0].DeltaR(jets[1]))
	_DRu2j1 = abs(muons[1].DeltaR(jets[0]))
	_DRu2j2 = abs(muons[1].DeltaR(jets[1]))

	_DPhiu1j1 = abs(muons[0].DeltaPhi(jets[0]))
	_DPhiu1j2 = abs(muons[0].DeltaPhi(jets[1]))
	_DPhiu2j1 = abs(muons[1].DeltaPhi(jets[0]))
	_DPhiu2j2 = abs(muons[1].DeltaPhi(jets[1]))

	[_Muujj1, _Muujj2,_MHuujj] = GetLLJJMasses(muons[0],muons[1],jets[0],jets[1])
	[[_MTuvjj1, _MTuvjj2], [_Muvjj, _MTuvjj],_MHuvjj] = GetLVJJMasses(muons[0],met,jets[0],jets[1])

	[_Meejj1, _Meejj2,_MHeejj] = GetLLJJMasses(electrons[0],electrons[1],jets[0],jets[1])
	[[_MTevjj1, _MTevjj2], [_Mevjj, _MTevjj],_MHevjj] = GetLVJJMasses(electrons[0],met,jets[0],jets[1])

	_Muujjavg = 0.5*(_Muujj1+_Muujj2)

	_genjetcount = 0
	if T.isData==0:
		_genjetcount = len(T.GenJetPt)

	# This MUST have the same structure as _kinematic variables!
	toreturn = [_ptmu1,_ptmu2,_ptel1,_ptel2,_ptj1,_ptj2,_ptmet]
	toreturn += [_etamu1,_etamu2,_etael1,_etael2,_etaj1,_etaj2,_etamet]
	toreturn += [_phimu1,_phimu2,_phiel1,_phiel2,_phij1,_phij2,_phimet]
	toreturn += [_isomu1,_isomu2]
	
	toreturn += [_chimu1,_chimu2]
	toreturn += [_ispfmu1,ispfmu2]
	toreturn += [_layersmu1,_layersmu2]

	toreturn += [_qmu1,_qmu2]
	toreturn += [_dptmu1,_dptmu2]
	toreturn += [_nhefj1,_nhefj2,_nemefj1,_nemefj2]
	toreturn += [_stuujj,_stuvjj]
	toreturn += [_steejj,_stevjj]
	toreturn += [_Muu,_MTuv]
	toreturn += [_DRuu,_DPHIuv,_DPHIj1v,_DPHIj2v]
	toreturn += [_DRu1j1,_DRu1j2,_DRu2j1,_DRu2j2]
	toreturn += [_DPhiu1j1,_DPhiu1j2,_DPhiu2j1,_DPhiu2j2]
	toreturn += [_Muujj1, _Muujj2,_Muujjavg]
	toreturn += [_MTuvjj1, _MTuvjj2,_Muvjj, _MTuvjj]
	toreturn += [_MHuujj,_MHuvjj]
	toreturn += [_Meejj1, _Meejj2]
	toreturn += [_MTevjj1, _MTevjj2,_Mevjj, _MTevjj]	
	toreturn += [_jetcount,_mucount,_elcount,_genjetcount]
	toreturn += [_ismuon_muon1,_ismuon_muon2]
	return toreturn



##########################################################################################
#################    BELOW IS THE ACTUAL LOOP OVER ENTRIES         #######################
##########################################################################################
startTime = datetime.now()

# Please don't edit here. It is static. The kinematic calulations are the only thing to edit!
lumisection = array.array("L",[0])
t.SetBranchAddress("ls",lumisection)
for n in range(N):

	# This is the loop over events. Due to the heavy use of functions and automation of 
	# systematic variations, this loop is very small. It should not really be editted, 
	# except possibly to add a new flag or weight variable. 
	# All editable contents concerning kinematics are in the function defs.

	# Get the entry
	t.GetEntry(n)
	# if n > 1000:  # Testing....
	# 	break
	if n%100==0:
		print 'Procesing event',n, 'of', N # where we are in the loop...

	## ===========================  BASIC SETUP  ============================= ##
	# print '-----'
	# Assign Weights
	Branches['weight_central'][0] = startingweight*GetPUWeight(t,'Central','Basic')
	Branches['weight_pu_down'][0] = startingweight*GetPUWeight(t,'SysDown','Basic')
	Branches['weight_pu_up'][0] = startingweight*GetPUWeight(t,'SysUp','Basic')
	Branches['weight_central_2012D'][0] = startingweight*GetPUWeight(t,'Central','2012D')
	Branches['weight_nopu'][0] = startingweight
	if dopdf:
		pdfweights = GetPDFWeights(t)
		for p in range(len(pdfweights)):
			Branches[_pdfweightsnames[p]][0] = pdfweights[p]
	
	# Event Flags
	Branches['run_number'][0]   = t.run
	# event_number[0] = int(t.event)
	Branches['event_number'][0] = t.event
	Branches['lumi_number'][0]  = lumisection[0]
	Branches['GoodVertexCount'][0] = CountVertices(t)




	if t.isData == True:
		Branches['pass_HLTMu40_eta2p1'][0] = PassTrigger(t,["HLT_Mu40_eta2p1_v"],1)         # Data Only
		Branches['passTriggerObjectMatching'][0]  = 1*(True in t.MuonHLTSingleMuonMatched)  # Data Only
		Branches['passBPTX0'][0]                  = 1*(t.isBPTX0)          # Unused, Data only: MC = 0
		Branches['passBeamScraping'][0]           = 1*(1-t.isBeamScraping) # Used, Data only
		Branches['passTrackingFailure'][0]        = 1*(1-t.isTrackingFailure) # Used, Data only
		Branches['passBadEESuperCrystal'][0]      = 1*(1-t.passBadEESupercrystalFilter) # Used, Data only
		Branches['passEcalLaserCorr'][0]          = 1*(t.passEcalLaserCorrFilter) # Used, Data only
		Branches['# passHcalLaserEvent'][0]         = 1*(1-t.passHcalLaserEventFilter) # Used, Data only
		Branches['passHcalLaserEvent'][0]         = 1 # Ooops, where did it go?
		Branches['passPhysDeclared'][0]           = 1*(t.isPhysDeclared)

	else:
		Branches['pass_HLTMu40_eta2p1'][0] = PassTrigger(t,["HLT_Mu40_eta2p1_v"],1)        
		Branches['passTriggerObjectMatching'][0]  = 1
		Branches['passBPTX0'][0]                  = 1
		Branches['passBeamScraping'][0]           = 1
		Branches['passTrackingFailure'][0]        = 1
		Branches['passBadEESuperCrystal'][0]      = 1
		Branches['passEcalLaserCorr'][0]          = 1
		Branches['passHcalLaserEvent'][0]         = 1
		Branches['passPhysDeclared'][0]           = 1
	
	Branches['passPrimaryVertex'][0]          = 1*(t.isPrimaryVertex)     # checked, data+MC
	Branches['passHBHENoiseFilter'][0]        = 1*(t.passHBHENoiseFilter) # checked, data+MC
	Branches['passBeamHalo'][0]               = 1*(t.passBeamHaloFilterTight) # checked, data+MC
	Branches['passEcalDeadCellBE'][0]         = 1*(1-t.passEcalDeadCellBoundaryEnergyFilter) # Checked, data + MC
	Branches['passEcalDeadCellTP'][0]         = 1*(1-t.passEcalDeadCellTriggerPrimitiveFilter) # Checked, data + MC

	Branches['passDataCert'][0] = 1
	if ( (t.isData==True) and (CheckRunLumiCert(t.run,lumisection[0]) == False) ) : 	
		Branches['passDataCert'][0] = 0



	## ===========================  Calculate everything!  ============================= ##

	# Looping over systematic variations
	for v in _variations:
		# All calucations are done here
		calculations = FullKinematicCalculation(t,v)
		# Now cleverly cast the variables
		for b in range(len(_kinematicvariables)):
			Branches[_kinematicvariables[b]+v][0] = calculations[b]

	## ===========================     Skim out events     ============================= ##

	# Feel like skimming? Do it here. The syntax is just Branches[branchname] > blah, or whatever condition
	# you want to impose. This Branches[blah] mapping was needed because branches must be linked to arrays of length [0]
	# BE MINDFUL: Just because the central (non-systematic) quantity meets the skim, does not mean 
	# that the systematic varied quantity will, and that will throw off systematics calculations later.
	# Make sure your skim is looser than any selection you will need afterward!

	if (Branches['Pt_muon1'][0] < 42): continue
	if nonisoswitch != True:
		if (Branches['Pt_muon2'][0] < 42) and (Branches['Pt_miss'][0] < 35): continue
	if (Branches['Pt_jet1'][0] < 110): continue
	if (Branches['Pt_jet2'][0] < 40): continue
	if (Branches['St_uujj'][0] < 250) and (Branches['St_uvjj'][0] < 250): continue
	# Fill output tree with event
	tout.Fill()

# All done. Write and close file.
tout.Write()
fout.Close()

# Timing, for debugging and optimization
print(datetime.now()-startTime)

print ('mv '+tmpfout+' '+finalfout)
os.system('mv '+tmpfout+' '+finalfout)
os.system('rm '+junkfile1)
os.system('rm '+junkfile2)
