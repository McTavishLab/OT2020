

from opentree import OT

import os
import sys
import json
import dendropy

from Bio import Entrez
Entrez.email = "ejmctavish@ucmerced.edu"

from pygbif import occurrences as occ


def get_tips_for_nodes(node_list):
    node_tips = {}
    for node in node_list:
        synth_sub = OT.synth_subtree(node_id=node, label_format="id")
        sub_tips = [leaf.taxon.label for leaf in synth_sub.tree.leaf_node_iter()]
        node_tips[node] = sub_tips
    return(node_tips)
    

def get_ncbi_records(ncbi_id):
    handle = Entrez.egquery(retmax=50, term="txid{}[Organism]".format(ncbi_id), idtype="acc")
    gen_record = Entrez.read(handle)
    eq_results = {}
    for db in gen_record['eGQueryResult']:
        try:
            count = int(db['Count'])
            if count > 0:
                eq_results[db['DbName']]=db
        except ValueError:
            pass
    return(eq_results)



def get_tip_info(ott_id, all_tax_dict):
    """For an ott_id and a dictionary with taxon info, 
    call ncbi and GBIF apis and return mini_dict"""
    tmp_dict = all_tax_dict[ott_id.strip('ott')]
    tmp_dict['ncbi_ids'] = []
    tmp_dict['gbif_ids'] = []   
    tmp_dict['ncbi_eq_results'] = []
    tmp_dict['gbif_records'] = 0
    for source in tmp_dict['source'].split(','):
        if source.startswith('ncbi'):
            ncbi_id = source.split(':')[1]
            tmp_dict['ncbi_ids'].append(ncbi_id)
            eq_results = get_ncbi_records(ncbi_id)
            tmp_dict['ncbi_eq_results'].append(eq_results)
        if source.startswith('gbif'):
            gbif_id = source.split(':')[1]
            tmp_dict['gbif_ids'].append(gbif_id)
            tmp_dict['gbif_records'] += occ.count(taxonKey = gbif_id)
    return tmp_dict    


def generate_node_annotations(nodes, node_tips, tip_dict):
    """Generate an annotations dictionary for a set of nodes.
    nodes_tip = a dictionary with keys that are node_ids listing all the tips descending from that node
    tip_dict = a dcitionary with infomration about each tip"""
    node_annotation = {}
    for nid in nodes:
        node_annotation[nid] = {}
        node_annotation[nid]['tips_counted'] = 0
        node_annotation[nid]['ncbi_ids'] = 0
        node_annotation[nid]['gbif_ids'] = 0
        node_annotation[nid]['genomes'] = 0
        node_annotation[nid]['genbank'] = 0
        node_annotation[nid]['gbif_occ'] = 0
        node_annotation[nid]['has_gbif_dat'] = 0
        node_annotation[nid]['has_gbif_id'] = 0
        node_annotation[nid]['has_nuc_dat'] = 0
        node_annotation[nid]['has_genome_dat'] = 0
        node_annotation[nid]['has_ncbi_id'] = 0
        node_annotation[nid]['total_descendents'] = len(node_tips[nid])
        for tip in node_tips[nid]:
            assert tip in tip_dict
            if tip in tip_dict:
                node_annotation[nid]['tips_counted'] += 1
                node_annotation[nid]['ncbi_ids'] +=len(tip_dict[tip].get('ncbi_ids',[]))
                tip_genomes = sum([int(res.get('genome',{'Count':0})['Count']) for res in tip_dict[tip]['ncbi_eq_results']])
                node_annotation[nid]['genomes'] += tip_genomes
                tip_genbank = sum([int(res.get('nuccore',{'Count':0})['Count']) for res in tip_dict[tip]['ncbi_eq_results']])
                node_annotation[nid]['genbank'] += tip_genbank
                node_annotation[nid]['gbif_occ'] += int(tip_dict[tip]['gbif_records'])
                node_annotation[nid]['gbif_ids'] +=len(tip_dict[tip].get('gbif_ids',[]))
                if len(tip_dict[tip].get('ncbi_ids',[])) >= 1:
                    node_annotation[nid]['has_ncbi_id'] += 1
                if len(tip_dict[tip].get('gbif_ids',[])) >= 1:
                    node_annotation[nid]['has_gbif_id'] += 1
                if int(tip_dict[tip]['gbif_records']) >= 1:
                    node_annotation[nid]['has_gbif_dat'] += 1
                if int(tip_genomes) >= 1:
                    node_annotation[nid]['has_genome_dat'] += 1
                if sum([int(res.get('nuccore',{'Count':0})['Count']) for res in tip_dict[tip]['ncbi_eq_results']]) >= 1:
                    node_annotation[nid]['has_nuc_dat'] +=1
        if node_annotation[nid]['tips_counted'] > 0:
            node_annotation[nid]['has_gbif_dat_perc'] = int((node_annotation[nid]['has_gbif_dat']/node_annotation[nid]['tips_counted'])*100)
            node_annotation[nid]['has_genome_dat_perc'] = float((node_annotation[nid]['has_genome_dat']/float(node_annotation[nid]['tips_counted']))*100)
            node_annotation[nid]['has_nuc_dat_perc'] = int((node_annotation[nid]['has_nuc_dat']/node_annotation[nid]['tips_counted'])*100)
            node_annotation[nid]['has_gbif_id_perc'] = int((node_annotation[nid]['has_gbif_id']/node_annotation[nid]['tips_counted'])*100)
            node_annotation[nid]['has_ncbi_id_perc'] = int((node_annotation[nid]['has_ncbi_id']/node_annotation[nid]['tips_counted'])*100)
        else:
            node_annotation[nid]['has_gbif_dat_perc'] = 0
            node_annotation[nid]['has_nuc_dat_perc'] = 0
            node_annotation[nid]['has_gbif_id_perc'] = 0
            node_annotation[nid]['has_ncbi_id_perc'] = 0
    return(node_annotation)
                

def write_itol_heatmap(filename, title, unit, node_annotation, param):
    """Write out an itol heatmap file to filename, with title and units label.
    annot dict must have keys which are node ids in tree on itol (may require underscore space subs..)
    param should be key of annot_dict[node_ids] = {}"""
    fi = open(filename, 'w')
    startstr = """DATASET_HEATMAP
    #In heatmaps, each ID is associated to multiple numeric values, which are displayed as a set of colored boxes defined by a color gradient
    #lines starting with a hash are comments and ignored during parsing
    #=================================================================#
    #                    MANDATORY SETTINGS                           #
    #=================================================================#
    #select the separator which is used to delimit the data below (TAB,SPACE or COMMA).This separator must be used throughout this file (except in the SEPARATOR line, which uses space).
    #SEPARATOR TAB
    SEPARATOR SPACE
    #SEPARATOR COMMA

    #label is used in the legend table (can be changed later)
    DATASET_LABEL {t}

    #dataset color (can be changed later)
    COLOR #ff0000

    #define labels for each individual field column
    FIELD_LABELS {u}

    #=================================================================#
    #                    OPTIONAL SETTINGS                            #
    #=================================================================#


    #Heatmaps can have an optional Newick formatted tree assigned. Its leaf IDs must exactly match the dataset FIELD_LABELS.
    #The tree will be used to sort the dataset fields, and will be displayed above the dataset. It can have branch lengths defined.
    #All newlines and spaces should be stripped from the tree, and COMMA cannot be used as the dataset separator if a FIELD_TREE is provided.
    #FIELD_TREE (((f1:0.2,f5:0.5):1,(f2:0.2,f3:0.3):1.2):0.5,(f4:0.1,f6:0.5):0.8):1;



    #=================================================================#
    #     all other optional settings can be set or changed later     #
    #           in the web interface (under 'Datasets' tab)           #
    #=================================================================#

    #Each dataset can have a legend, which is defined using LEGEND_XXX fields below
    #For each row in the legend, there should be one shape, color and label.
    #Optionally, you can define an exact legend position using LEGEND_POSITION_X and LEGEND_POSITION_Y. To use automatic legend positioning, do NOT define these values
    #Optionally, shape scaling can be present (LEGEND_SHAPE_SCALES). For each shape, you can define a scaling factor between 0 and 1.
    #Shape should be a number between 1 and 6, or any protein domain shape definition.
    #1: square
    #2: circle
    #3: star
    #4: right pointing triangle
    #5: left pointing triangle
    #6: checkmark

    #LEGEND_TITLE,Dataset legend
    #LEGEND_POSITION_X,100
    #LEGEND_POSITION_Y,100
    #LEGEND_SHAPES,1,2,3
    #LEGEND_COLORS,#ff0000,#00ff00,#0000ff
    #LEGEND_LABELS,value1,value2,value3
    #LEGEND_SHAPE_SCALES,1,1,0.5

    #left margin, used to increase/decrease the spacing to the next dataset. Can be negative, causing datasets to overlap.
    #MARGIN 0

    #width of the individual boxes
    #STRIP_WIDTH 25

    #always show internal values; if set, values associated to internal nodes will be displayed even if these nodes are not collapsed. It could cause overlapping in the dataset display.
    #SHOW_INTERNAL 0


    #show dashed lines between leaf labels and the dataset
    #DASHED_LINES 1

    #if a FIELD_TREE is present, it can be hidden by setting this option to 0
    #SHOW_TREE 1

    #define the color for the NULL values in the dataset. Use the letter X in the data to define the NULL values
    #COLOR_NAN #000000

    #automatically create and display a legend based on the color gradients and values defined below
    #AUTO_LEGEND 1


    #define the heatmap gradient colors. Values in the dataset will be mapped onto the corresponding color gradient.
    COLOR_MIN #0000ff
    COLOR_MAX #ff0000

    #you can specify a gradient with three colors (e.g red to yellow to green) by setting 'USE_MID_COLOR' to 1, and specifying the midpoint color
    #USE_MID_COLOR 1
    #COLOR_MID #ffff00

    #By default, color gradients will be calculated based on dataset values. You can force different values to use in the calculation by setting the values below:
    #USER_MIN_VALUE 0
    #USER_MID_VALUE 500
    #USER_MAX_VALUE 1000

    #border width; if set above 0, a border of specified width (in pixels) will be drawn around individual cells
    #BORDER_WIDTH,0

    #border color; used only when BORDER_WIDTH is above 0
    #BORDER_COLOR,#0000ff


    #Internal tree nodes can be specified using IDs directly, or using the 'last common ancestor' method described in iTOL help pages
    #=================================================================#
    #       Actual data follows after the "DATA" keyword              #
    #=================================================================#
    DATA\n
    """.format(t=title, u=unit)
    fi.write(startstr)
    for node in node_annotation:
        desc = node_annotation[node][param]
        fi.write("{} {}\n".format(node, desc))    
    fi.close()
