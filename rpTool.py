import numpy as np
import tempfile
import logging
import pandas as pd
from sklearn.metrics import jaccard_score

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s.%(msecs)03d %(levelname)s %(module)s - %(funcName)s: %(message)s',
    datefmt='%d-%m-%Y %H:%M:%S',
)

logging.getLogger().setLevel(logging.DEBUG)

## Compute the Jaccard index similarity coefficient score between two MIRIAM dicts
# 1.0 is a perfect match and 0.0 is a complete miss
# We assume that the meas has the "complete" information and simulated has the incomplete info
#TODO: interchange meas and sim since actually the measured has inclomple info and sim has more info
def jaccardMIRIAM(meas_miriam, sim_miriam):
    values = list(set([ x for y in list(meas_miriam.values())+list(sim_miriam.values()) for x in y]))
    meas_data = {}
    sim_data = {}
    for key in set(list(meas_miriam.keys())+list(sim_miriam.keys())):
        tmp_meas_row = []
        tmp_sim_row = []
        for value in values:
            if key in meas_miriam:
                if value in meas_miriam[key]:
                    tmp_meas_row.append(1)
                else:
                    tmp_meas_row.append(0)
            else:
                tmp_meas_row.append(0)
            if key in sim_miriam:
                if value in sim_miriam[key]:
                    tmp_sim_row.append(1)
                else:
                    tmp_sim_row.append(0)
            else:
                tmp_sim_row.append(0)
        meas_data[key] = tmp_meas_row       
        sim_data[key] = tmp_sim_row     
    meas_dataf = pd.DataFrame(meas_data, index=values)
    sim_dataf = pd.DataFrame(sim_data, index=values)
    #return meas_dataf, sim_dataf, jaccard_score(meas_dataf, sim_dataf, average='weighted')
    return jaccard_score(meas_dataf, sim_dataf, average='weighted')




## Match all the measured chemical species to the simulated chemical species between two SBML 
#
# WARNING: Here we assume that two species cannot have multiple matches -- TODO: change to allow multiple matches and return the best scoring one 
#
def compareSpecies(measured_rpsbml, sim_rpsbml):
    ############## compare species ###################
    meas_species_match = {}
    species_match = {}
    for measured_species in measured_rpsbml.model.getListOfSpecies():
        logging.info('--- Trying to match chemical species: '+str(measured_species.getId())+' ---')
        meas_species_match[measured_species.getId()] = {}
        species_match[measured_species.getId()] = {'id': None, 'score': 0.0, 'found': False}
        for sim_species in sim_rpsbml.model.getListOfSpecies():
            meas_species_match[measured_species.getId()][sim_species.getId()] = {'score': 0.0, 'found': False}
            measured_brsynth_annot = sim_rpsbml.readBRSYNTHAnnotation(measured_species.getAnnotation())
            sim_rpsbml_brsynth_annot = sim_rpsbml.readBRSYNTHAnnotation(sim_species.getAnnotation())
            measured_miriam_annot = sim_rpsbml.readMIRIAMAnnotation(measured_species.getAnnotation()) 
            sim_miriam_annot = sim_rpsbml.readMIRIAMAnnotation(sim_species.getAnnotation())
            #find according to xref
            #logging.info('=====================================')
            #logging.info('Measured MIRIAM: '+str(sim_rpsbml.readMIRIAMAnnotation(measured_species.getAnnotation())))
            #logging.info('Simulated MIRIAM: '+str(sim_rpsbml.readMIRIAMAnnotation(sim_species.getAnnotation())))
            #### MIRIAM ####
            if sim_rpsbml.compareMIRIAMAnnotations(measured_species.getAnnotation(), sim_species.getAnnotation()):
                logging.info('--> Matched MIRIAM: '+str(sim_species.getId()))
                #meas_species_match[measured_species.getId()][sim_species.getId()]['score'] += 0.4
                meas_species_match[measured_species.getId()][sim_species.getId()]['score'] += 0.4*jaccardMIRIAM(sim_miriam_annot, measured_miriam_annot)
                meas_species_match[measured_species.getId()][sim_species.getId()]['found'] = True
            #logging.info('=====================================')
            ##### InChIKey ##########
            #find according to the inchikey -- allow partial matches
            if 'inchikey' in measured_brsynth_annot and 'inchikey' in sim_rpsbml_brsynth_annot:
                measured_inchikey_split = measured_brsynth_annot['inchikey'].split('-')
                sim_rpsbml_inchikey_split = sim_rpsbml_brsynth_annot['inchikey'].split('-')
                if measured_inchikey_split[0]==sim_rpsbml_inchikey_split[0]:
                    logging.info('Matched first layer InChIkey: ('+str(measured_brsynth_annot['inchikey'])+' -- '+str(sim_rpsbml_brsynth_annot['inchikey'])+')')
                    meas_species_match[measured_species.getId()][sim_species.getId()]['score'] += 0.2
                    if measured_inchikey_split[1]==sim_rpsbml_inchikey_split[1]:
                        logging.info('Matched second layer InChIkey: ('+str(measured_brsynth_annot['inchikey'])+' -- '+str(sim_rpsbml_brsynth_annot['inchikey'])+')')
                        meas_species_match[measured_species.getId()][sim_species.getId()]['score'] += 0.2
                        meas_species_match[measured_species.getId()][sim_species.getId()]['found'] = True
                        if measured_inchikey_split[2]==sim_rpsbml_inchikey_split[2]:
                            logging.info('Matched third layer InChIkey: ('+str(measured_brsynth_annot['inchikey'])+' -- '+str(sim_rpsbml_brsynth_annot['inchikey'])+')')
                            meas_species_match[measured_species.getId()][sim_species.getId()]['score'] += 0.2
                            meas_species_match[measured_species.getId()][sim_species.getId()]['found'] = True
            if species_match[measured_species.getId()]['score']<meas_species_match[measured_species.getId()][sim_species.getId()]['score'] and meas_species_match[measured_species.getId()][sim_species.getId()]['found']:
                logging.info('Measured species '+str(measured_species.getId())+' ('+str(species_match[measured_species.getId()]['score'])+') match has found a better score '+str(sim_species.getId())+' ('+str(meas_species_match[measured_species.getId()][sim_species.getId()]['score'])+')')
                species_match[measured_species.getId()]['id'] = sim_species.getId()
                species_match[measured_species.getId()]['score'] = round(meas_species_match[measured_species.getId()][sim_species.getId()]['score'], 4)
                species_match[measured_species.getId()]['found'] = meas_species_match[measured_species.getId()][sim_species.getId()]['found']
    logging.info('species_match:')
    logging.info(species_match)
    logging.info('-----------------------')
    return species_match


##
# Compare that all the measured species of a reactions are found within sim species to match with a reaction.
# We assume that there cannot be two reactions that have the same species and reactants. This is maintained by SBML
# Compare also by EC number, from the third ec to the full EC
# v2 -> compare all the reactions
def compareReactions(measured_rpsbml, sim_rpsbml, species_match, pathway_id='rp_pathway'):
    #TODO: need to deal if there are more than one match
    ############## compare the reactions #######################
    #construct sim reactions with species
    logging.info('------ Comparing reactions --------')
    #match the reactants and products conversion to sim species
    measured_reactions_match = {}
    for measured_reaction_id in measured_rpsbml.readRPpathwayIDs(pathway_id):
        logging.info('Species match of measured reaction: '+str(measured_reaction_id))
        measured_reaction = measured_rpsbml.model.getReaction(measured_reaction_id)
        measured_reaction_miriam = sim_rpsbml.readMIRIAMAnnotation(measured_reaction.getAnnotation())
        ################ construct the dict transforming the species #######
        measured_reactions_match[measured_reaction_id] = {'reactants': {},
                                                          'reactants_score': 0.0,
                                                          'products': {},
                                                          'products_score': 0.0,
                                                          'species_score': 0.0,
                                                          'species_std': 0.0,
                                                          'species_reaction': None,
                                                          'ec_score': 0.0,
                                                          'ec_reaction': None,
                                                          'found': False}
        logging.info('\t+++++++ Species match +++++++')
        for sim_reaction_id in sim_rpsbml.readRPpathwayIDs(pathway_id):
            logging.info('\t=========== '+str(sim_reaction_id)+' ==========')
            sim_reaction = sim_rpsbml.model.getReaction(sim_reaction_id)
            sim_reactants_id = [reactant.species for reactant in sim_reaction.getListOfReactants()]
            sim_products_id = [product.species for product in sim_reaction.getListOfProducts()]
            tmp_reactants = {}
            tmp_products = {}
            one_missing = False
            ############ species ############
            logging.info('\tspecies_match: '+str(species_match.keys()))
            logging.info('\tsim_reactants_id: '+str(sim_reactants_id))
            logging.info('\tmeasured_reactants_id: '+str([i.species for i in measured_reaction.getListOfReactants()]))
            logging.info('\tsim_products_id: '+str(sim_products_id))
            logging.info('\tmeasured_products_id: '+str([i.species for i in measured_reaction.getListOfProducts()]))
            for reactant in measured_reaction.getListOfReactants():
                if reactant.species in species_match:
                    if species_match[reactant.species]['id'] in sim_reactants_id:
                        tmp_reactants[reactant.species] = species_match[reactant.species]
                        logging.info('\t\tMatched measured reactant species: '+str(reactant.species)+' with simulated species: '+str(species_match[reactant.species]['id']))
                    else:
                        logging.info('\t\tCould not find the folowing measured reactant in the currrent reaction: '+str(reactant.species))
                        one_missing = True
                        break
                else:
                    logging.info('\t\tCould not find the following measured reactant in the matched species: '+str(reactant.species))
                    one_missing = True
                    break
            if one_missing:
                continue
            for product in measured_reaction.getListOfProducts():
                if product.species in species_match:
                    if species_match[product.species]['id'] in sim_products_id:
                        tmp_products[product.species] = species_match[product.species]
                        logging.info('\t\tMatched measured product species: '+str(product.species)+' with simulated species: '+str(species_match[product.species]['id']))
                    else:
                        logging.info('\t\tCould not find the folowing measured product in the currrent reaction: '+str(product.species))
                        one_missing = True
                        break
                else:
                    logging.info('\t\tCould not find the following measured product in the matched species: '+str(product.species))
                    one_missing = True
                    break
            if one_missing:
                continue
            logging.info('\t--> Succesfullly matched all reactants and products')
            measured_reactions_match[measured_reaction_id]['reactants'] = tmp_reactants
            measured_reactions_match[measured_reaction_id]['products'] = tmp_products
            reactants_score = [measured_reactions_match[measured_reaction_id]['reactants'][i]['score'] for i in measured_reactions_match[measured_reaction_id]['reactants']]
            measured_reactions_match[measured_reaction_id]['reactants_score'] = np.mean(reactants_score)
            products_score = [measured_reactions_match[measured_reaction_id]['products'][i]['score'] for i in measured_reactions_match[measured_reaction_id]['products']]
            measured_reactions_match[measured_reaction_id]['products_score'] = np.mean(products_score)
            ### calculate pathway species score
            measured_reactions_match[measured_reaction_id]['species_score'] = np.mean(reactants_score+products_score)
            measured_reactions_match[measured_reaction_id]['species_std'] = np.std(reactants_score+products_score)
            measured_reactions_match[measured_reaction_id]['species_reaction'] = sim_reaction_id
            measured_reactions_match[measured_reaction_id]['found'] = True
            break #only if we assume that one match is all that can happen TODO: calculate all matches and take the highest scoring one
            #continue #if you want the match to be more continuous
        ########## EC number ############
        #Warning we only match a single reaction at a time -- assume that there cannot be more than one to match at a given time
        logging.info('\t+++++ EC match +++++++')
        if 'ec-code' in measured_reaction_miriam:
            for sim_reaction_id in sim_rpsbml.readRPpathwayIDs(pathway_id):
                logging.info('\t=========== '+str(sim_reaction_id)+' ==========')
                sim_reaction = sim_rpsbml.model.getReaction(sim_reaction_id)
                sim_reaction_miriam = sim_rpsbml.readMIRIAMAnnotation(sim_reaction.getAnnotation())
                if 'ec-code' in sim_reaction_miriam:
                    #we only need one match here
                    measured_ec = [i for i in measured_reaction_miriam['ec-code']]
                    sim_ec = [i for i in sim_reaction_miriam['ec-code']]
                    #perfect match - one can have multiple ec score per reaction
                    logging.info('\tMeasured EC: '+str(measured_ec))
                    logging.info('\tSimulated EC: '+str(sim_ec))
                    if any(i in measured_ec for i in sim_ec) and measured_reactions_match[measured_reaction_id]['ec_score']<1.0:
                        measured_reactions_match[measured_reaction_id]['found'] = True
                        measured_reactions_match[measured_reaction_id]['ec_reaction'] = sim_reaction_id
                        measured_reactions_match[measured_reaction_id]['ec_score'] = 1.0
                        logging.info('\t--> EC match (perfect) between measured reaction: '+str(measured_reaction_id)+' and simulated reaction: '+str(sim_reaction_id))
                        break #only if you assume that one match is all that is possible
                        #continue if you want the match to be more continuous
                    ### partial match ####
                    measured_frac_ec = [i.split('.')[:-1] for i in measured_reaction_miriam['ec-code']]
                    measured_frac_ec = ['.'.join(i) for i in measured_frac_ec]
                    sim_frac_ec = [i.split('.')[:-1] for i in sim_reaction_miriam['ec-code']]
                    sim_frac_ec = ['.'.join(i) for i in sim_frac_ec]
                    #up to the third ec
                    if any(i in measured_frac_ec for i in sim_frac_ec) and measured_reactions_match[measured_reaction_id]['ec_score']<0.5:
                        measured_reactions_match[measured_reaction_id]['found'] = True
                        measured_reactions_match[measured_reaction_id]['ec_reaction'] = sim_reaction_id
                        measured_reactions_match[measured_reaction_id]['ec_score'] = 0.5
                        logging.info('\t--> EC match (third) between measured reaction: '+str(measured_reaction_id)+' and simulated reaction: '+str(sim_reaction_id))
                        break #only if you assume that one match is all that is possible
                        #continue #if you want to have more continuous
    #### compile a reaction score based on the ec and species scores
    logging.info(measured_reactions_match)
    logging.info('-------------------------------')
    return measured_reactions_match


## Compare a measured to sim rpSBML pathway 
#
# Works by trying to find a measured pathway contained within a simulated one. Does not perform perfect match! Since 
# simulated ones contain full cofactors while the measured ones have impefect information
def compareRPpathways(measured_rpsbml, sim_rpsbml, strict_length=True, pathway_id='rp_pathway'):
    logging.info('##################### '+str(sim_rpsbml.model.getId())+' ######################')
    penalty_length = 1.0
    if strict_length:
        if not len(measured_rpsbml.readRPpathwayIDs(pathway_id))==len(sim_rpsbml.readRPpathwayIDs(pathway_id)):
            return False, 0.0, {}
    else:
        #calculate the penatly score for the legnth of the pathways not being the same length
        meas_path_length = len(measured_rpsbml.readRPpathwayIDs(pathway_id))
        sim_path_length = len(sim_rpsbml.readRPpathwayIDs(pathway_id))
        #add a penatly to the length only if the simulated pathway is longer than the measured one
        #if its smaller then we will not be able to retreive all reactions and the scor will not be good in any case
        #if meas_path_length<sim_path_length:
        penalty_length = 1.0-np.abs(meas_path_length-sim_path_length)/meas_path_length 
    species_match = compareSpecies(measured_rpsbml, sim_rpsbml)
    reactions_match = compareReactions(measured_rpsbml, sim_rpsbml, species_match, pathway_id)
    global_score = []
    global_found = []
    for measured_reaction_id in reactions_match:
        #make sure that EC and reaction match are the same
        if reactions_match[measured_reaction_id]['ec_reaction'] and reactions_match[measured_reaction_id]['species_reaction']:
            try:
                assert reactions_match[measured_reaction_id]['ec_reaction']==reactions_match[measured_reaction_id]['species_reaction']
            except AssertionError:
                logging.error(measured_rpsbml.model.getId())
                logging.error(sim_rpsbml.model.getId())
                logging.error(reactions_match[measured_reaction_id])
                logging.error(reactions_match[measured_reaction_id]['ec_reaction'])
                logging.error(reactions_match[measured_reaction_id]['species_reaction'])
        #assume 80% in the species and 20% for EC
        global_score.append(np.average([reactions_match[measured_reaction_id]['species_score'], reactions_match[measured_reaction_id]['ec_score']], weights=[0.8, 0.2]))
        global_found.append(reactions_match[measured_reaction_id]['found'])
    '''
    glo = {}
    glo['global_species_score'] = np.mean([reactions_match[i]['species_score'] for i in reactions_match])
    try:
        glo['global_species_score2'] = np.average([reactions_match[i]['species_score'] for i in reactions_match], weights=[reactions_match[i]['species_std'] for i in reactions_match])
    except ZeroDivisionError:
        glo['global_species_score2'] = -1.0
    glo['global_ec_score'] = np.mean([reactions_match[i]['ec_score'] for i in reactions_match])
    glo['reaction_match'] = reactions_match
    '''
    if all(global_found):
        return True, np.mean(global_score)*penalty_length, reactions_match
    else:
        return False, np.mean(global_score)*penalty_length, reactions_match