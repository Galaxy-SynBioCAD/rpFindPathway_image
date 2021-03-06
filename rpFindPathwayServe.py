import tarfile
import tempfile
import glob
import logging
from rdkit.Chem import MolFromSmiles, MolFromInchi, MolToSmiles, MolToInchi, MolToInchiKey, AddHs


import rpSBML
import rpFindPathway

logging.basicConfig(
    #level=logging.DEBUG,
    #level=logging.WARNING,
    level=logging.ERROR,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
)



##
#
#
def runFindPathway_hdd(measured_rpsbml_path, inputTar, pathway_id='rp_pathway', species_group_id='central_species'):
    dict_global = {}
    with tempfile.TemporaryDirectory() as tmpOutputFolder:
        tar = tarfile.open(inputTar, 'r')
        tar.extractall(path=tmpOutputFolder)
        tar.close()
        measured_rpsbml = rpSBML.rpSBML('measured')
        measured_rpsbml.readSBML(measured_rpsbml_path)
        for sbml_path in glob.glob(tmpOutputFolder+'/*'):
            fileName = sbml_path.split('/')[-1].replace('.sbml', '').replace('.rpsbml', '').replace('.xml', '')
            rpsbml = rpSBML.rpSBML(fileName)
            rpsbml.readSBML(sbml_path)
            score, all_match = rpFindPathway.compareOrderedReactions(measured_rpsbml, rpsbml, pathway_id, species_group_id)
            #if score>0.0:
            dict_global[fileName] = {'score': score, 'found': all_match}
            #dict_global[fileName] = {'reactions_score': reactions_score, 'reactions_std': reactions_std, 'reactions_ec_score': reactions_ec_score, 'reactions_ec_std': reactions_ec_std, 'dict_result': dict_result}
    return dict_global


#########################################################################################################
############################################## UTILITIES ################################################
#########################################################################################################


## Convert chemical depiction to others type of depictions
#
# Usage example:
# - convert_depiction(idepic='CCO', otype={'inchi', 'smiles', 'inchikey'})
# - convert_depiction(idepic='InChI=1S/C2H6O/c1-2-3/h3H,2H2,1H3', itype='inchi', otype={'inchi', 'smiles', 'inchikey'})
#
#  @param self The onject pointer
#  @param idepic string depiction to be converted, str
#  @param itype type of depiction provided as input, str
#  @param otype types of depiction to be generated, {"", "", ..}
#  @return odepic generated depictions, {"otype1": "odepic1", ..}
def convert_depiction(idepic, itype='smiles', otype={'inchikey'}):
    # Import (if needed)
    if itype == 'smiles':
        rdmol = MolFromSmiles(idepic, sanitize=True)
    elif itype == 'inchi':
        rdmol = MolFromInchi(idepic, sanitize=True)
    else:
        #raise NotImplementedError('"{}" is not a valid input type'.format(itype))
        logging.error('"{}" is not a valid input type'.format(itype))
        return {}
    if rdmol is None:  # Check imprt
        #raise NotImplementedError('Import error from depiction "{}" of type "{}"'.format(idepic, itype))
        logging.error('Import error from depiction "{}" of type "{}"'.format(idepic, itype))
        return {}
    # Export
    odepic = dict()
    for item in otype:
        if item == 'smiles':
            odepic[item] = MolToSmiles(rdmol)  # MolToSmiles is tricky, one mays want to check the possible options..
        elif item == 'inchi':
            odepic[item] = MolToInchi(rdmol)
        elif item == 'inchikey':
            odepic[item] = MolToInchiKey(rdmol)
        else:
            #raise NotImplementedError('"{}" is not a valid output type'.format(otype))
            logging.error('"{}" is not a valid output type'.format(otype))
            return {}
    return odepic


#########################################################################################################
############################################## MAKE SBML ################################################
#########################################################################################################
'''
These are the functions that make the SBML files from a dict input. These could be only species, reactions or pathway
'''


'''
example input: {'input_type': {'input_format': 'tar'}, 'search': {'db_name': 'chebi', 'id': '38407', 'inchi': 'InChI=1S/C6H6O4/c7-5(8)3-1-2-4-6(9)10/h1-4H,(H,7,8)(H,9,10)/b3-1+,4-2+', 'search_type': 'species'}, 'output_type': {'output_format': 'csv'}, 'adv': {'pathway_id': 'rp_pathway'}}

'''
def makeSpecies(dict_species,
                pathway_id='rp_pathway',
                species_group_id='central_species'):
    # not important -- tmp SBML for the comparison algorithm
    comp_xref = {}
    compartment_id = 'MNXC3'
    rpsbml = rpSBML.rpSBML('tmp')
    upper_flux_bound = 999999
    lower_flux_bound = 0
    ######
    rpsbml.genericModel('tmp',
                        'tmp',
                        comp_xref,
                        compartment_id,
                        upper_flux_bound,
                        lower_flux_bound)
    rpsbml.createPathway(pathway_id)
    rpsbml.createPathway(species_group_id)
    resConv = convert_depiction(idepic=dict_species['inchi'], itype='inchi', otype={'smiles', 'inchikey'})
    rpsbml.createSpecies(dict_species['db_name']+'_'+dict_species['id'],
                         compartment_id,
                         dict_species['db_name']+'_'+dict_species['id'],
                         {dict_species['db_name']: [dict_species['id']]},
                         dict_species['inchi'],
                         resConv['inchikey'],
                         resConv['smiles'],
                         species_group_id)
    return rpsbml


'''
example input: {'input_type': {'input_format': 'tar'}, 'search': {'ec': [{'id': '1.1.1.1'}], 'reactants': [{'db_name': 'chebi', 'id': '17333', 'inchi': 'InChI=1S/C6H6O4/c7-5(8)3-1-2-4-6(9)10/h1-4H,(H,7,8)(H,9,10)/b3-1+,4-2+'}], 'products': [{'db_name': 'chebi', 'id': '38407', 'inchi': 'InChI=1S/C6H6O4/c7-5(8)3-1-2-4-6(9)10/h1-4H,(H,7,8)(H,9,10)/b3-1+,4-2+'}], 'search_type': 'reaction'}, 'output_type': {'output_format': 'csv'}, 'adv': {'pathway_id': 'rp_pathway'}}

'''
def makeReaction(dict_reaction,
                 pathway_id='rp_pathway',
                 species_group_id='central_species'):
    # not important -- tmp SBML for the comparison algorithm
    comp_xref = {}
    compartment_id = 'MNXC3'
    rpsbml = rpSBML.rpSBML('tmp')
    upper_flux_bound = 999999
    lower_flux_bound = 0
    ######
    rpsbml.genericModel('tmp',
                        'tmp',
                        comp_xref,
                        compartment_id,
                        upper_flux_bound,
                        lower_flux_bound)
    rpsbml.createPathway(pathway_id)
    rpsbml.createPathway(species_group_id)
    for species in dict_reaction['reactants']+dict_reaction['products']:
        resConv = convert_depiction(idepic=species['inchi'], itype='inchi', otype={'smiles', 'inchikey'})
        rpsbml.createSpecies(species['db_name']+'_'+species['id'],
                             compartment_id,
                             species['db_name']+'_'+species['id'],
                             {species['db_name']: [species['id']]},
                             species['inchi'],
                             resConv['inchikey'],
                             resConv['smiles'],
                             species_group_id)
    '''
    example step: {'left': {'MNXM21': 1}, 'right': {'MNXM725924': 1}, 'rule_id': None, 'rule_ori_reac': None, 'rule_score': None, 'path_id': 142, 'step': 6, 'sub_step': None}
    {i['db_name']+'_'+i['id']: 1 for i in b['reactants']}
    '''
    rpsbml.createReaction('matchReac_1',
                          upper_flux_bound,
                          lower_flux_bound,
                          {'left': {i['db_name']+'_'+i['id']: 1 for i in dict_reaction['reactants']},
                           'right': {i['db_name']+'_'+i['id']: 1 for i in dict_reaction['products']},
                           'rule_id': None,
                           'rule_ori_reac': None,
                           'rule_score': None,
                           'path_id': 1,
                           'step': 1,
                           'sub_step': None},
                          compartment_id,
                          reacXref={'ec': [i['id'] for i in dict_reaction['ec']]},
                          pathway_id=pathway_id)
    return rpsbml


'''
example input: {'input_type': {'input_format': 'tar'}, 'search': {'reactions': [{'ec': [{'id': '1.1.1.1'}], 'reactants': [{'name': 'one', 'db_name': 'mnx', 'id': 'MNXM3', 'inchi': 'InChI=1S/C6H6O4/c7-5(8)3-1-2-4-6(9)10/h1-4H,(H,7,8)(H,9,10)/b3-1+,4-2+'}], 'products': [{'name': 'two', 'db_name': 'mnx', 'id': 'MNXM4', 'inchi': 'InChI=1S/C6H6O4/c7-5(8)3-1-2-4-6(9)10/h1-4H,(H,7,8)(H,9,10)/b3-1+,4-2+'}]}, {'ec': [{'id': '2.2.2.2'}], 'reactants': [{'name': 'three', 'db_name': 'mnx', 'id': 'MNXM4', 'inchi': 'InChI=1S/C6H6O4/c7-5(8)3-1-2-4-6(9)10/h1-4H,(H,7,8)(H,9,10)/b3-1+,4-2+'}], 'products': [{'name': 'four', 'db_name': 'mnx', 'id': 'MNXM5', 'inchi': 'InChI=1S/C6H6O4/c7-5(8)3-1-2-4-6(9)10/h1-4H,(H,7,8)(H,9,10)/b3-1+,4-2+'}]}], 'search_type': 'pathway'}, 'output_type': {'output_format': 'csv'}, 'adv': {'pathway_id': 'rp_pathway'}}
'''
def makePathway(dict_pathway,
                pathway_id='rp_pathway',
                species_group_id='central_species'):
    # not important -- tmp SBML for the comparison algorithm
    comp_xref = {}
    compartment_id = 'MNXC3'
    rpsbml = rpSBML.rpSBML('tmp')
    upper_flux_bound = 999999
    lower_flux_bound = 0
    ######
    rpsbml.genericModel('tmp',
                        'tmp',
                        comp_xref,
                        compartment_id,
                        upper_flux_bound,
                        lower_flux_bound)
    rpsbml.createPathway(pathway_id)
    rpsbml.createPathway(species_group_id)
    already_added = []
    for reaction in dict_pathway['reactions']:
        logging.debug(reaction['reactants'])
        logging.debug(reaction['products'])
        for species in reaction['reactants']+reaction['products']:
            if not species['db_name']+'_'+species['id'] in already_added: 
                already_added.append(species['db_name']+'_'+species['id'])
                resConv = convert_depiction(idepic=species['inchi'], itype='inchi', otype={'smiles', 'inchikey'})
                rpsbml.createSpecies(species['db_name']+'_'+species['id'],
                                     compartment_id,
                                     'tmp_name',
                                     {species['db_name']: [species['id']]},
                                     species['inchi'],
                                     resConv['inchikey'],
                                     resConv['smiles'],
                                     species_group_id)
    '''
    example step: {'left': {'MNXM21': 1}, 'right': {'MNXM725924': 1}, 'rule_id': None, 'rule_ori_reac': None, 'rule_score': None, 'path_id': 142, 'step': 6, 'sub_step': None}
    {i['db_name']+'_'+i['id']: 1 for i in b['reactants']}
    '''
    rp_count = 1
    for reaction in dict_pathway['reactions']:
        rpsbml.createReaction('matchReac_'+str(rp_count),
                              upper_flux_bound,
                              lower_flux_bound,
                              {'left': {i['db_name']+'_'+i['id']: 1 for i in reaction['reactants']},
                               'right': {i['db_name']+'_'+i['id']: 1 for i in reaction['products']},
                               'rule_id': None,
                               'rule_ori_reac': None,
                               'rule_score': None,
                               'path_id': 1,
                               'step': 1,
                               'sub_step': None},
                              compartment_id,
                              reacXref={'ec': [i['id'] for i in reaction['ec']]},
                              pathway_id=pathway_id)
        rp_count += 1
    return rpsbml


#########################################################################################################
################################################# FIND ##################################################
#########################################################################################################


##
#
#
'''
example output --> {"rp_5_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_15_2": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_12_8": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_6_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_13_2": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_21_4": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_14_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_17_3": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_20_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_8_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_19_2": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_11_2": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_7_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_23_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_22_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_1_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_16_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_9_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_2_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_10_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_4_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_18_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}, "rp_3_1": {"chebi_15531__64__MNXC3": {"MNXM40__64__MNXC3": 0.4087}}}

'''
def findSpecies(measured_rpsbml,
                inputTar,
                pathway_id='rp_pathway',
                species_group_id='central_species'):
    dict_global = {}
    with tempfile.TemporaryDirectory() as tmpOutputFolder:
        tar = tarfile.open(inputTar, 'r')
        tar.extractall(path=tmpOutputFolder)
        tar.close()
        for sbml_path in glob.glob(tmpOutputFolder+'/*'):
            fileName = sbml_path.split('/')[-1].replace('.sbml', '').replace('.rpsbml', '').replace('.xml', '')
            rpsbml = rpSBML.rpSBML(fileName)
            rpsbml.readSBML(sbml_path)
            dict_global[fileName] = rpFindPathway.compareSpecies(measured_rpsbml, rpsbml)
            logging.debug('################# '+str(fileName)+' ###################')
            logging.debug(dict_global[fileName])
            logging.debug('######################################')
    return dict_global
    


'''
    "rp_2_7": {
        "id": [
            "RP1",
            "RP2"
        ],
        "score": 0.65185,
        "found": true
    },
    "rp_16_9": {
        "id": [
            "RP1",
            "RP2",
            "RP3"
        ],
        "score": 0.65185,
        "found": tru
...
'''
##
#
#
def findReaction(measured_rpsbml,
                 inputTar,
                 pathway_id='rp_pathway',
                 species_group_id='central_species'):
    dict_global = {}
    with tempfile.TemporaryDirectory() as tmpOutputFolder:
        tar = tarfile.open(inputTar, 'r')
        tar.extractall(path=tmpOutputFolder)
        tar.close()
        for sbml_path in glob.glob(tmpOutputFolder+'/*'):
            fileName = sbml_path.split('/')[-1].replace('.sbml', '').replace('.rpsbml', '').replace('.xml', '')
            rpsbml = rpSBML.rpSBML(fileName)
            rpsbml.readSBML(sbml_path)
            species_match = rpFindPathway.compareSpecies(measured_rpsbml, rpsbml)
            reaction_match, tmp_reaction_match = rpFindPathway.compareReactions(measured_rpsbml, rpsbml, species_match, pathway_id)
            assert len(reaction_match)==1
            assert 'matchReac_1' in reaction_match
            dict_global[fileName] = reaction_match['matchReac_1']
            logging.debug('################# '+str(fileName)+' ###################')
            logging.debug(dict_global[fileName])
            logging.debug('######################################')
    return dict_global



'''
example output:
{
    "rp_5_1": [
        0.22885200000000006,
        false
    ],
    "rp_15_2": [
        0.1373112,
        false
    ],
...
'''
## Find the pathway that is the closest to the input pathway in an ordered fashion
#TODO: consider having first the comparison in an ordered fashion and then in an unordered fashion
#
def findOrderedPathway(measured_rpsbml,
                       inputTar,
                       pathway_id='rp_pathway',
                       species_group_id='central_species'):
    dict_global = {}
    with tempfile.TemporaryDirectory() as tmpOutputFolder:
        tar = tarfile.open(inputTar, 'r')
        tar.extractall(path=tmpOutputFolder)
        tar.close()
        for sbml_path in glob.glob(tmpOutputFolder+'/*'):
            fileName = sbml_path.split('/')[-1].replace('.sbml', '').replace('.rpsbml', '').replace('.xml', '')
            rpsbml = rpSBML.rpSBML(fileName)
            rpsbml.readSBML(sbml_path)
            species_match = rpFindPathway.compareSpecies(measured_rpsbml, rpsbml)
            dict_global[fileName] = rpFindPathway.compareOrderedPathways(measured_rpsbml,
                                                                         rpsbml,
                                                                         pathway_id,
                                                                         species_group_id)
            logging.debug('################# '+str(fileName)+' ###################')
            logging.debug(dict_global[fileName])
            logging.debug('######################################')
    return dict_global

'''
example output:
{
    "rp_5_1": [ 
        0.22885333333333335,
        true
    ],
    "rp_15_2": [
        0.13731199999999996,
        true
    ],
...
'''
## Function to find the pathways closest to the unordered collection of reactions
#
#
def findReactions(measured_rpsbml,
                  inputTar,
                  pathway_id='rp_pathway'):
    dict_global = {}
    with tempfile.TemporaryDirectory() as tmpOutputFolder:
        tar = tarfile.open(inputTar, 'r')
        tar.extractall(path=tmpOutputFolder)
        tar.close()
        for sbml_path in glob.glob(tmpOutputFolder+'/*'):
            fileName = sbml_path.split('/')[-1].replace('.sbml', '').replace('.rpsbml', '').replace('.xml', '')
            rpsbml = rpSBML.rpSBML(fileName)
            rpsbml.readSBML(sbml_path)
            species_match = rpFindPathway.compareSpecies(measured_rpsbml, rpsbml)
            dict_global[fileName] = rpFindPathway.compareUnorderedpathways(measured_rpsbml,
                                                                           rpsbml,
                                                                           pathway_id)
            logging.debug('################# '+str(fileName)+' ###################')
            logging.debug(dict_global[fileName])
            logging.debug('######################################')
    return dict_global
