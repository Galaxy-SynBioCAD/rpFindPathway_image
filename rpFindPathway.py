import numpy as np
import tempfile
import logging
import pandas as pd
from sklearn.metrics import jaccard_score
import rpGraph


######################################################################################################################
############################################## UTILITIES #############################################################
######################################################################################################################

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


## Function to find the unique species
#
# pd_matrix is organised such that the rows are the simulated species and the columns are the measured ones
#
def findUniqueRowColumn(pd_matrix):
    logging.debug(pd_matrix)
    to_ret = {}
    ######################## filter by the global top values ################
    logging.debug('################ Filter best #############')
    #transform to np.array
    x = pd_matrix.values
    #resolve the rouding issues to find the max
    x = np.around(x, decimals=5)
    #first round involves finding the highest values and if found set to 0.0 the rows and columns (if unique)
    top = np.where(x==np.max(x))
    #as long as its unique keep looping
    if np.count_nonzero(x)==0:
        return to_ret
    while len(top[0])==1 and len(top[1])==1: 
        if np.count_nonzero(x)==0:
            return to_ret
        pd_entry = pd_matrix.iloc[[top[0][0]],[top[1][0]]]
        row_name = str(pd_entry.index[0])
        col_name = str(pd_entry.columns[0])
        if col_name in to_ret:
            logging.debug('Overwriting (1): '+str(col_name))
            logging.debug(x)
        to_ret[col_name] = [row_name]
        #delete the rows and the columns 
        logging.debug('==================')
        logging.debug('Column: '+str(col_name))
        logging.debug('Row: '+str(row_name))
        pd_matrix.loc[:, col_name] = 0.0
        pd_matrix.loc[row_name, :] = 0.0
        x = pd_matrix.values
        x = np.around(x, decimals=5)
        top = np.where(x==np.max(x))
        logging.debug(pd_matrix)
        logging.debug(top)
        logging.debug('==================')
    #################### filter by columns (measured) top values ##############
    logging.debug('################ Filter by column best ############')
    x = pd_matrix.values
    x = np.around(x, decimals=5)
    if np.count_nonzero(x)==0:
        return to_ret
    reloop = True
    while reloop:
        if np.count_nonzero(x)==0:
            return to_ret
        reloop = False
        for col in range(len(x[0])):
            if np.count_nonzero(x[:,col])==0:
                continue
            top_row = np.where(x[:,col]==np.max(x[:,col]))[0]
            if len(top_row)==1:
                top_row = top_row[0]
                #if top_row==0.0:
                #    continue
                #check to see if any other measured pathways have the same or larger score (accross)
                row = list(x[top_row, :])
                #remove current score consideration
                row.pop(col)
                if max(row)>=x[top_row, col]:
                    logging.warning('For col '+str(col)+' there are either better or equal values: '+str(row))
                    logging.warning(x)
                    continue
                #if you perform any changes on the rows and columns, then you can perform the loop again
                reloop = True
                pd_entry = pd_matrix.iloc[[top_row],[col]]
                logging.debug('==================')
                row_name = pd_entry.index[0]
                col_name = pd_entry.columns[0]
                logging.debug('Column: '+str(col_name))
                logging.debug('Row: '+str(row_name))
                if col_name in to_ret:
                    logging.debug('Overwriting (2): '+str(col_name))
                    logging.debug(pd_matrix.values)
                to_ret[col_name] = [row_name]
                #delete the rows and the columns 
                pd_matrix.loc[:, col_name] = 0.0
                pd_matrix.loc[row_name, :] = 0.0
                x = pd_matrix.values
                x = np.around(x, decimals=5)
                logging.debug(pd_matrix)
                logging.debug('==================')
    ################## laslty if there are multiple values that are not 0.0 then account for that ######
    logging.debug('################# get the rest ##########')
    x = pd_matrix.values
    x = np.around(x, decimals=5)
    if np.count_nonzero(x)==0:
        return to_ret
    for col in range(len(x[0])):
        if not np.count_nonzero(x[:,col])==0:
            top_rows = np.where(x[:,col]==np.max(x[:,col]))[0]
            if len(top_rows)==1:
                top_row = top_rows[0]
                pd_entry = pd_matrix.iloc[[top_row],[col]]
                row_name = pd_entry.index[0]
                col_name = pd_entry.columns[0]
                if not col_name in to_ret:
                    to_ret[col_name] = [row_name]
                else:
                    logging.warning('At this point should never have only one: '+str(x[:,col]))
                    logging.warning(x)
            else:
                for top_row in top_rows:
                    pd_entry = pd_matrix.iloc[[top_row],[col]]
                    row_name = pd_entry.index[0]
                    col_name = pd_entry.columns[0]
                    if not col_name in to_ret:
                        to_ret[col_name] = []
                    to_ret[col_name].append(row_name)
    logging.debug(pd_matrix)
    logging.debug('###################')
    return to_ret


######################################################################################################################
############################################### SPECIES ##############################################################
######################################################################################################################


## Match all the measured chemical species to the simulated chemical species between two SBML 
#
# TODO: for all the measured species compare with the simualted one. Then find the measured and simulated species that match the best and exclude the 
# simulated species from potentially matching with another
#
def compareSpecies(measured_rpsbml, sim_rpsbml, measured_comp_id=None, sim_comp_id=None):
    ############## compare species ###################
    meas_sim = {}
    sim_meas = {}
    species_match = {}
    for measured_species in measured_rpsbml.model.getListOfSpecies():
        #skip the species that are not in the right compartmennt, if specified
        if measured_comp_id and not measured_species.getCompartment()==measured_comp_id:
            continue
        logging.debug('--- Trying to match chemical species: '+str(measured_species.getId())+' ---')
        meas_sim[measured_species.getId()] = {}
        species_match[measured_species.getId()] = {}
        #species_match[measured_species.getId()] = {'id': None, 'score': 0.0, 'found': False}
        #TODO: need to exclude from the match if a simulated chemical species is already matched with a higher score to another measured species
        for sim_species in sim_rpsbml.model.getListOfSpecies():
            #skip the species that are not in the right compartmennt, if specified
            if sim_comp_id and not sim_species.getCompartment()==sim_comp_id:
                continue
            meas_sim[measured_species.getId()][sim_species.getId()] = {'score': 0.0, 'found': False}
            if not sim_species.getId() in sim_meas:
                sim_meas[sim_species.getId()] = {}
            sim_meas[sim_species.getId()][measured_species.getId()] = {'score': 0.0, 'found': False}
            measured_brsynth_annot = sim_rpsbml.readBRSYNTHAnnotation(measured_species.getAnnotation())
            sim_rpsbml_brsynth_annot = sim_rpsbml.readBRSYNTHAnnotation(sim_species.getAnnotation())
            measured_miriam_annot = sim_rpsbml.readMIRIAMAnnotation(measured_species.getAnnotation())
            sim_miriam_annot = sim_rpsbml.readMIRIAMAnnotation(sim_species.getAnnotation())
            #### MIRIAM ####
            if sim_rpsbml.compareMIRIAMAnnotations(measured_species.getAnnotation(), sim_species.getAnnotation()):
                logging.debug('--> Matched MIRIAM: '+str(sim_species.getId()))
                #meas_sim[measured_species.getId()][sim_species.getId()]['score'] += 0.4
                meas_sim[measured_species.getId()][sim_species.getId()]['score'] += 0.2+0.2*jaccardMIRIAM(sim_miriam_annot, measured_miriam_annot)
                meas_sim[measured_species.getId()][sim_species.getId()]['found'] = True
            ##### InChIKey ##########
            #find according to the inchikey -- allow partial matches
            #compare either inchikey in brsynth annnotation or MIRIAM annotation
            #NOTE: here we prioritise the BRSynth annotation inchikey over the MIRIAM
            measured_inchikey_split = None
            sim_rpsbml_inchikey_split = None
            if 'inchikey' in measured_brsynth_annot: 
                measured_inchikey_split = measured_brsynth_annot['inchikey'].split('-')
            elif 'inchikey' in measured_miriam_annot:
                if not len(measured_miriam_annot['inchikey'])==1:
                    #TODO: handle mutliple inchikey with mutliple compare and the highest comparison value kept
                    logging.warning('There are multiple inchikey values, taking the first one: '+str(measured_miriam_annot['inchikey']))
                measured_inchikey_split = measured_miriam_annot['inchikey'][0].split('-')
            if 'inchikey' in sim_rpsbml_brsynth_annot:
                sim_rpsbml_inchikey_split = sim_rpsbml_brsynth_annot['inchikey'].split('-')
            elif 'inchikey' in sim_miriam_annot:
                if not len(sim_miriam_annot['inchikey'])==1:
                    #TODO: handle mutliple inchikey with mutliple compare and the highest comparison value kept
                    logging.warning('There are multiple inchikey values, taking the first one: '+str(sim_rpsbml_brsynth_annot['inchikey']))
                sim_rpsbml_inchikey_split = sim_miriam_annot['inchikey'][0].split('-')
            if measured_inchikey_split and sim_rpsbml_inchikey_split:
                if measured_inchikey_split[0]==sim_rpsbml_inchikey_split[0]:
                    logging.debug('Matched first layer InChIkey: ('+str(measured_inchikey_split)+' -- '+str(sim_rpsbml_inchikey_split)+')')
                    meas_sim[measured_species.getId()][sim_species.getId()]['score'] += 0.2
                    if measured_inchikey_split[1]==sim_rpsbml_inchikey_split[1]:
                        logging.debug('Matched second layer InChIkey: ('+str(measured_inchikey_split)+' -- '+str(sim_rpsbml_inchikey_split)+')')
                        meas_sim[measured_species.getId()][sim_species.getId()]['score'] += 0.2
                        meas_sim[measured_species.getId()][sim_species.getId()]['found'] = True
                        if measured_inchikey_split[2]==sim_rpsbml_inchikey_split[2]:
                            logging.debug('Matched third layer InChIkey: ('+str(measured_inchikey_split)+' -- '+str(sim_rpsbml_inchikey_split)+')')
                            meas_sim[measured_species.getId()][sim_species.getId()]['score'] += 0.2
                            meas_sim[measured_species.getId()][sim_species.getId()]['found'] = True
            sim_meas[sim_species.getId()][measured_species.getId()]['score'] = meas_sim[measured_species.getId()][sim_species.getId()]['score']
            sim_meas[sim_species.getId()][measured_species.getId()]['found'] = meas_sim[measured_species.getId()][sim_species.getId()]['found']
    #build the matrix to send
    meas_sim_mat = {}
    for i in meas_sim:
        meas_sim_mat[i] = {}
        for y in meas_sim[i]:
            meas_sim_mat[i][y] = meas_sim[i][y]['score']
    unique = findUniqueRowColumn(pd.DataFrame(meas_sim_mat))
    logging.debug('findUniqueRowColumn:')
    logging.debug(unique)
    for meas in meas_sim:
        if meas in unique:
            species_match[meas] = {}
            for unique_spe in unique[meas]:
                species_match[meas][unique_spe] = round(meas_sim[meas][unique[meas][0]]['score'], 5)
        else:
            logging.warning('Cannot find a species match for the measured species: '+str(meas))
    logging.debug('#########################')
    logging.debug('species_match:')
    logging.debug(species_match)
    logging.debug('-----------------------')
    return species_match

######################################################################################################################
############################################# REACTION ###############################################################
######################################################################################################################


##
# Compare that all the measured species of a reactions are found within sim species to match with a reaction.
# We assume that there cannot be two reactions that have the same species and reactants. This is maintained by SBML
# Compare also by EC number, from the third ec to the full EC
# TODO: need to remove from the list reactions simulated reactions that have matched
def compareReactions(measured_rpsbml, sim_rpsbml, species_match, pathway_id='rp_pathway'):
    ############## compare the reactions #######################
    #construct sim reactions with species
    logging.debug('------ Comparing reactions --------')
    #match the reactants and products conversion to sim species
    tmp_reaction_match = {}
    meas_sim = {}
    sim_meas = {}
    for measured_reaction_id in measured_rpsbml.readRPpathwayIDs(pathway_id):
        logging.debug('Species match of measured reaction: '+str(measured_reaction_id))
        measured_reaction = measured_rpsbml.model.getReaction(measured_reaction_id)
        measured_reaction_miriam = measured_rpsbml.readMIRIAMAnnotation(measured_reaction.getAnnotation())
        ################ construct the dict transforming the species #######
        meas_sim[measured_reaction_id] = {}
        tmp_reaction_match[measured_reaction_id] = {}
        for sim_reaction_id in sim_rpsbml.readRPpathwayIDs(pathway_id):
            if not sim_reaction_id in sim_meas:
                sim_meas[sim_reaction_id] = {}
            sim_meas[sim_reaction_id][measured_reaction_id] = {}
            meas_sim[measured_reaction_id][sim_reaction_id] = {}
            logging.debug('\t=========== '+str(sim_reaction_id)+' ==========')
            logging.debug('\t+++++++ Species match +++++++')
            tmp_reaction_match[measured_reaction_id][sim_reaction_id] = {'reactants': {},
                                                                         'reactants_score': 0.0,
                                                                         'products': {},
                                                                         'products_score': 0.0,
                                                                         'species_score': 0.0,
                                                                         'species_std': 0.0,
                                                                         'species_reaction': None,
                                                                         'ec_score': 0.0,
                                                                         'ec_reaction': None,
                                                                         'score': 0.0,
                                                                         'found': False}
            sim_reaction = sim_rpsbml.model.getReaction(sim_reaction_id)
            sim_reactants_id = [reactant.species for reactant in sim_reaction.getListOfReactants()]
            sim_products_id = [product.species for product in sim_reaction.getListOfProducts()]
            ############ species ############
            logging.debug('\tspecies_match: '+str(species_match))
            logging.debug('\tspecies_match: '+str(species_match.keys()))
            logging.debug('\tsim_reactants_id: '+str(sim_reactants_id))
            logging.debug('\tmeasured_reactants_id: '+str([i.species for i in measured_reaction.getListOfReactants()]))
            logging.debug('\tsim_products_id: '+str(sim_products_id))
            logging.debug('\tmeasured_products_id: '+str([i.species for i in measured_reaction.getListOfProducts()]))
            #ensure that the match is 1:1
            #1)Here we assume that a reaction cannot have twice the same species
            cannotBeSpecies = []
            #if there is a match then we loop again since removing it from the list of potential matches would be appropriate
            keep_going = True
            while keep_going:
                logging.debug('\t\t----------------------------')
                keep_going = False
                for reactant in measured_reaction.getListOfReactants():
                    logging.debug('\t\tReactant: '+str(reactant.species))
                    #if a species match has been found AND if such a match has been found
                    founReaIDs = [tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][i]['id'] for i in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'] if not tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][i]['id']==None]
                    logging.debug('\t\tfounReaIDs: '+str(founReaIDs))
                    if reactant.species and reactant.species in species_match and not list(species_match[reactant.species].keys())==[] and not reactant.species in founReaIDs:
                        #return all the similat entries
                        '''
                        speMatch = list(set(species_match[reactant.species].keys())&set(sim_reactants_id))
                        speMatch = list(set(speMatch)-set(cannotBeSpecies))
                        logging.debug('\t\tspeMatch: '+str(speMatch))
                        if len(speMatch)==1:
                            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][reactant.species] = {'id': speMatch[0], 'score': species_match[reactant.species]['score'], 'found': True}
                            cannotBeSpecies.append(speMatch[0])
                            keep_going = True
                            logging.debug('\t\tMatched measured reactant species: '+str(reactant.species)+' with simulated species: '+str(speMatch[0])) 
                        elif not reactant.species in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants']:
                            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][reactant.species] = {'id': None, 'score': 0.0, 'found': False}
                            #logging.debug('\t\tCould not find the folowing measured reactant in the currrent reaction: '+str(reactant.species))
                        '''
                        best_spe = [k for k, v in sorted(species_match[reactant.species].items(), key=lambda item: item[1], reverse=True)][0]
                        tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][reactant.species] = {'id': best_spe, 'score': species_match[reactant.species][best_spe], 'found': True}
                        cannotBeSpecies.append(best_spe)
                    elif not reactant.species in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants']:
                        logging.warning('\t\tCould not find the following measured reactant in the matched species: '+str(reactant.species))
                        tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][reactant.species] = {'id': None, 'score': 0.0, 'found': False}
                for product in measured_reaction.getListOfProducts():
                    logging.debug('\t\tProduct: '+str(product.species))
                    foundProIDs = [tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'][i]['id'] for i in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'] if not tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'][i]['id']==None]
                    logging.debug('\t\tfoundProIDs: '+str(foundProIDs))
                    if product.species and product.species in species_match and not list(species_match[product.species].keys())==[] and not product.species in foundProIDs:
                        '''
                        #return all the similat entries
                        speMatch = list(set(species_match[product.species]['id'])&set(sim_products_id))
                        speMatch = list(set(speMatch)-set(cannotBeSpecies))
                        logging.debug('\t\tspeMatch: '+str(speMatch))
                        if len(speMatch)==1:
                            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'][product.species] = {'id': speMatch[0], 'score': species_match[product.species]['score'], 'found': True}
                            cannotBeSpecies.append(speMatch[0])
                            keep_going = True
                            logging.debug('\t\tMatched measured product species: '+str(product.species)+' with simulated species: '+str(speMatch[0]))    
                        elif not product.species in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products']:
                            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'][product.species] = {'id': None, 'score': 0.0, 'found': False}
                            #logging.debug('\t\tCould not find the following measured product in the matched species: '+str(product.species))
                        '''
                        best_spe = [k for k, v in sorted(species_match[product.species].items(), key=lambda item: item[1], reverse=True)][0]
                        tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][product.species] = {'id': best_spe, 'score': species_match[product.species][best_spe], 'found': True}
                        cannotBeSpecies.append(best_spe)
                    elif not product.species in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products']:
                        logging.warning('\t\tCould not find the following measured product in the matched species: '+str(product.species))
                        tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'][product.species] = {'id': None, 'score': 0.0, 'found': False}
                logging.debug('\t\tcannotBeSpecies: '+str(cannotBeSpecies))
            reactants_score = [tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][i]['score'] for i in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants']]
            reactants_found = [tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants'][i]['found'] for i in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants']]
            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['reactants_score'] = np.mean(reactants_score)
            products_score = [tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'][i]['score'] for i in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products']]
            products_found = [tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products'][i]['found'] for i in tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products']]
            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['products_score'] = np.mean(products_score)
            ### calculate pathway species score
            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['species_score'] = np.mean(reactants_score+products_score)
            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['species_std'] = np.std(reactants_score+products_score)
            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['species_reaction'] = sim_reaction_id
            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['found'] = all(reactants_found+products_found)
            #tmp_reaction_match[measured_reaction_id][sim_reaction_id]['found'] = True
            #break #only if we assume that one match is all that can happen TODO: calculate all matches and take the highest scoring one
            #continue #if you want the match to be more continuous
            ########## EC number ############
            #Warning we only match a single reaction at a time -- assume that there cannot be more than one to match at a given time
            logging.debug('\t+++++ EC match +++++++')
            if 'ec-code' in measured_reaction_miriam:
                sim_reaction = sim_rpsbml.model.getReaction(sim_reaction_id)
                sim_reaction_miriam = sim_rpsbml.readMIRIAMAnnotation(sim_reaction.getAnnotation())
                if 'ec-code' in sim_reaction_miriam:
                    #we only need one match here
                    measured_ec = [i for i in measured_reaction_miriam['ec-code']]
                    sim_ec = [i for i in sim_reaction_miriam['ec-code']]
                    #perfect match - one can have multiple ec score per reaction - keep the score for the highest matching one
                    logging.debug('\t~~~~~~~~~~~~~~~~~~~~')
                    logging.debug('\tMeasured EC: '+str(measured_ec))
                    logging.debug('\tSimulated EC: '+str(sim_ec)) 
                    measured_frac_ec = [[y for y in ec.split('.') if not y=='-'] for ec in measured_reaction_miriam['ec-code']]
                    sim_frac_ec = [[y for y in ec.split('.') if not y=='-'] for ec in sim_reaction_miriam['ec-code']]
                    #complete the ec numbers with None to be length of 4
                    for i in range(len(measured_frac_ec)):
                        for y in range(len(measured_frac_ec[i]),4):
                            measured_frac_ec[i].append(None)
                    for i in range(len(sim_frac_ec)):
                        for y in range(len(sim_frac_ec[i]),4):
                            sim_frac_ec[i].append(None)
                    logging.debug('\t'+str(measured_frac_ec))
                    logging.debug('\t'+str(sim_frac_ec))
                    best_ec_compare = {'meas_ec': [], 'sim_ec': [], 'score': 0.0, 'found': False}
                    for ec_m in measured_frac_ec:
                        for ec_s in sim_frac_ec:
                            tmp_score = 0.0
                            for i in range(4):
                                if not ec_m[i]==None and not ec_s[i]==None:
                                    if ec_m[i]==ec_s[i]:
                                        tmp_score += 0.25
                                        if i==2:
                                            best_ec_compare['found'] = True
                                    else:
                                        break
                            if tmp_score>best_ec_compare['score']:
                                best_ec_compare['meas_ec'] = ec_m
                                best_ec_compare['sim_ec'] = ec_s
                                best_ec_compare['score'] = tmp_score
                    logging.debug('\t'+str(best_ec_compare))
                    if best_ec_compare['found']:
                        tmp_reaction_match[measured_reaction_id][sim_reaction_id]['found'] = True
                    tmp_reaction_match[measured_reaction_id][sim_reaction_id]['ec_reaction'] = sim_reaction_id
                    tmp_reaction_match[measured_reaction_id][sim_reaction_id]['ec_score'] = best_ec_compare['score']
                    logging.debug('\t~~~~~~~~~~~~~~~~~~~~')
            #WRNING: Here 80% for species match and 20% for ec match
            tmp_reaction_match[measured_reaction_id][sim_reaction_id]['score'] = np.average([tmp_reaction_match[measured_reaction_id][sim_reaction_id]['species_score'], tmp_reaction_match[measured_reaction_id][sim_reaction_id]['ec_score']], weights=[0.8, 0.2])
            sim_meas[sim_reaction_id][measured_reaction_id] = tmp_reaction_match[measured_reaction_id][sim_reaction_id]['score']
            meas_sim[measured_reaction_id][sim_reaction_id] = tmp_reaction_match[measured_reaction_id][sim_reaction_id]['score']
    ### matrix compare #####
    unique = findUniqueRowColumn(pd.DataFrame(meas_sim))
    logging.debug('findUniqueRowColumn')
    logging.debug(unique)
    reaction_match = {} 
    for meas in meas_sim:
        reaction_match[meas] = {'id': None, 'score': 0.0, 'found': False}
        if meas in unique:
            #if len(unique[meas])>1:
            #    logging.debug('Multiple values may match, choosing the first arbitrarily')
            reaction_match[meas]['id'] = unique[meas]
            reaction_match[meas]['score'] = round(tmp_reaction_match[meas][unique[meas][0]]['score'], 5)
            reaction_match[meas]['found'] = tmp_reaction_match[meas][unique[meas][0]]['found']
    #### compile a reaction score based on the ec and species scores
    logging.debug(tmp_reaction_match)
    logging.debug(reaction_match)
    logging.debug('-------------------------------')
    return reaction_match, tmp_reaction_match



## Compare individual reactions and see if the measured pathway is contained within the simulated one
#
# Note that we assure that the match is 1:1 between species using the species match

#
def compareReaction_graph(species_match, meas_reac, sim_reac):
    scores = []
    all_match = True
    ########### reactants #######
    ignore_reactants = []
    for meas_reactant in meas_reac.getListOfReactants():
        if meas_reactant.species in species_match:
            spe_found = False
            for sim_reactant in sim_reac.getListOfReactants():
                if sim_reactant.species in species_match[meas_reactant.species] and not sim_reactant.species in ignore_reactants:
                    scores.append(species_match[meas_reactant.species][sim_reactant.species])
                    ignore_reactants.append(sim_reactant.species)
                    spe_found = True
                    break
            if not spe_found:
                scores.append(0.0)
                all_match = False
        else:
            logging.debug('Cannot find the measured species '+str(meas_reactant.species)+' in the the matched species: '+str(species_match))
            scores.append(0.0)
            all_match = False
    #products
    ignore_products = []
    for meas_product in meas_reac.getListOfProducts():
        if meas_product.species in species_match:
            pro_found = False
            for sim_product in sim_reac.getListOfProducts():
                if sim_product.species in species_match[meas_product.species] and not sim_product.species in ignore_products:
                    scores.append(species_match[meas_product.species][sim_product.species])
                    ignore_products.append(sim_product.species)
                    pro_found = True
                    break
            if not pro_found:
                scores.append(0.0)
                all_match = False
        else:
            logging.debug('Cannot find the measured species '+str(meas_product.species)+' in the the matched species: '+str(species_match))
            scores.append(0.0)
            all_match = False
    return np.mean(scores), all_match


######################################################################################################################
############################################### EC NUMBER ############################################################
######################################################################################################################

def compareEC(meas_reac_miriam, sim_reac_miriam):
    #Warning we only match a single reaction at a time -- assume that there cannot be more than one to match at a given time
    if 'ec-code' in meas_reac_miriam and 'ec-code' in sim_reac_miriam:
        measured_frac_ec = [[y for y in ec.split('.') if not y=='-'] for ec in meas_reac_miriam['ec-code']]
        sim_frac_ec = [[y for y in ec.split('.') if not y=='-'] for ec in sim_reac_miriam['ec-code']]
        #complete the ec numbers with None to be length of 4
        for i in range(len(measured_frac_ec)):
            for y in range(len(measured_frac_ec[i]), 4):
                measured_frac_ec[i].append(None)
        for i in range(len(sim_frac_ec)):
            for y in range(len(sim_frac_ec[i]), 4):
                sim_frac_ec[i].append(None)
        logging.debug('Measured: ')
        logging.debug(measured_frac_ec)
        logging.debug('Simulated: ')
        logging.debug(sim_frac_ec)
        best_ec_compare = {'meas_ec': [], 'sim_ec': [], 'score': 0.0, 'found': False}
        for ec_m in measured_frac_ec:
            for ec_s in sim_frac_ec:
                tmp_score = 0.0
                for i in range(4):
                    if not ec_m[i]==None and not ec_s[i]==None:
                        if ec_m[i]==ec_s[i]:
                            tmp_score += 0.25
                            if i==2:
                                best_ec_compare['found'] = True
                        else:
                            break
                if tmp_score>best_ec_compare['score']:
                    best_ec_compare['meas_ec'] = ec_m
                    best_ec_compare['sim_ec'] = ec_s
                    best_ec_compare['score'] = tmp_score
        return best_ec_compare['score']
    else:
        logging.warning('One of the two reactions does not have any EC entries.\nMeasured: '+str(meas_reac_miriam)+' \nSimulated: '+str(sim_reac_miriam))
        return 0.0


######################################################################################################################
################################################# PATHWAYS ###########################################################
######################################################################################################################


##
#
# Note: remember that we are trying to find the measured species equivalent
#
def compareOrderedPathways(measured_rpsbml,
                           sim_rpsbml,
                           pathway_id='rp_pathway',
                           species_group_id='central_species'):
    measured_rpgraph = rpGraph.rpGraph(measured_rpsbml, pathway_id, species_group_id)
    sim_rpgraph = rpGraph.rpGraph(sim_rpsbml, pathway_id, species_group_id)
    measured_ordered_reac = measured_rpgraph.orderedRetroReactions()
    sim_ordered_reac = sim_rpgraph.orderedRetroReactions()
    species_match = compareSpecies(measured_rpsbml, sim_rpsbml)
    scores = []
    if len(measured_ordered_reac)>len(sim_ordered_reac):
        for i in range(len(sim_ordered_reac)):
            logging.debug('measured_ordered_reac['+str(i)+']: '+str(measured_ordered_reac))
            logging.debug('sim_ordered_reac['+str(i)+']: '+str(sim_ordered_reac))
            spe_score, is_full_match = compareReaction_graph(species_match, 
                                                             measured_rpsbml.model.getReaction(measured_ordered_reac[i]), 
                                                             sim_rpsbml.model.getReaction(sim_ordered_reac[i]))
            ec_score = compareEC(measured_rpsbml.readMIRIAMAnnotation(measured_rpsbml.model.getReaction(measured_ordered_reac[i]).getAnnotation()),
                                 sim_rpsbml.readMIRIAMAnnotation(sim_rpsbml.model.getReaction(sim_ordered_reac[i]).getAnnotation()))
            scores.append(np.average([spe_score, ec_score], weights=[0.8, 0.2]))
        return np.mean(scores)*( 1.0-np.abs(len(measured_ordered_reac)-len(sim_ordered_reac))/len(measured_ordered_reac) ), False
    elif len(measured_ordered_reac)<len(sim_ordered_reac):
        for i in range(len(measured_ordered_reac)):
            logging.debug('measured_ordered_reac['+str(i)+']: '+str(measured_ordered_reac))
            logging.debug('sim_ordered_reac['+str(i)+']: '+str(sim_ordered_reac))
            spe_score, is_full_match = compareReaction_graph(species_match, 
                                                             measured_rpsbml.model.getReaction(measured_ordered_reac[i]), 
                                                             sim_rpsbml.model.getReaction(sim_ordered_reac[i]))
            ec_score = compareEC(measured_rpsbml.readMIRIAMAnnotation(measured_rpsbml.model.getReaction(measured_ordered_reac[i]).getAnnotation()),
                                 sim_rpsbml.readMIRIAMAnnotation(sim_rpsbml.model.getReaction(sim_ordered_reac[i]).getAnnotation()))
            scores.append(np.average([spe_score, ec_score], weights=[0.8, 0.2]))
        return np.mean(scores)*( 1.0-np.abs(len(measured_ordered_reac)-len(sim_ordered_reac))/len(sim_ordered_reac) ), False
    #if the pathways are of the same length is the only time when the match may be perfect
    elif len(measured_ordered_reac)==len(sim_ordered_reac):
        perfect_match = True
        for i in range(len(sim_ordered_reac)):
            logging.debug('measured_ordered_reac['+str(i)+']: '+str(measured_ordered_reac))
            logging.debug('sim_ordered_reac['+str(i)+']: '+str(sim_ordered_reac))
            spe_score, is_full_match = compareReaction_graph(species_match, 
                                                             measured_rpsbml.model.getReaction(measured_ordered_reac[i]), 
                                                             sim_rpsbml.model.getReaction(sim_ordered_reac[i]))
            ec_score = compareEC(measured_rpsbml.readMIRIAMAnnotation(measured_rpsbml.model.getReaction(measured_ordered_reac[i]).getAnnotation()),
                                 sim_rpsbml.readMIRIAMAnnotation(sim_rpsbml.model.getReaction(sim_ordered_reac[i]).getAnnotation()))
            scores.append(np.average([spe_score, ec_score], weights=[0.8, 0.2]))
            if ec_score==0.0 and not is_full_match:
                prefect_match = False
        return np.mean(scores), perfect_match


## Compare a measured to sim rpSBML pathway 
#
# Works by trying to find a measured pathway contained within a simulated one. Does not perform perfect match! Since 
# simulated ones contain full cofactors while the measured ones have impefect information
def compareUnorderedpathways(measured_rpsbml,
                             sim_rpsbml,
                             pathway_id='rp_pathway'):
    logging.debug('##################### '+str(sim_rpsbml.model.getId())+' ######################')
    penalty_length = 1.0
    #calculate the penatly score for the legnth of the pathways not being the same length
    meas_path_length = len(measured_rpsbml.readRPpathwayIDs(pathway_id))
    sim_path_length = len(sim_rpsbml.readRPpathwayIDs(pathway_id))
    #add a penatly to the length only if the simulated pathway is longer than the measured one
    #if its smaller then we will not be able to retreive all reactions and the scor will not be good in any case
    #if meas_path_length<sim_path_length:
    if meas_path_length>sim_path_length:
        penalty_length = 1.0-np.abs(meas_path_length-sim_path_length)/meas_path_length
    elif meas_path_length<=sim_path_length:
        penalty_length = 1.0-np.abs(meas_path_length-sim_path_length)/sim_path_length
    species_match = compareSpecies(measured_rpsbml, sim_rpsbml)
    reaction_match, all_rection_match_info = compareReactions(measured_rpsbml, sim_rpsbml, species_match, pathway_id)
    logging.debug(penalty_length)
    logging.debug([reaction_match[i]['score'] for i in reaction_match])
    logging.debug([reaction_match[i]['found'] for i in reaction_match])
    global_score = np.mean([reaction_match[i]['score'] for i in reaction_match])
    global_found = [reaction_match[i]['found'] for i in reaction_match]
    return np.mean(global_score)*penalty_length, all(global_found)
