#
#   Copyright (c) 2010-2013, MIT Probabilistic Computing Project
#
#   Lead Developers: Jay Baxter and Dan Lovell
#   Authors: Jay Baxter, Dan Lovell, Baxter Eaves, Vikash Mansinghka
#   Research Leads: Vikash Mansinghka, Patrick Shafto
#
#   Licensed under the Apache License, Version 2.0 (the "License");
#   you may not use this file except in compliance with the License.
#   You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
#   Unless required by applicable law or agreed to in writing, software
#   distributed under the License is distributed on an "AS IS" BASIS,
#   WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#   See the License for the specific language governing permissions and
#   limitations under the License.
#

import engine as be
import re
import pickle
import gzip
import utils
import os

class Parser(object):
    def __init__(self):
        self.engine_method_names = [method_name for method_name in be.get_method_names() if method_name[0] != '_']
        self.parser_method_names = [method_name[6:] for method_name in dir(Parser) if method_name[:6] == 'parse_']
        self.method_names = set(self.engine_method_names).intersection(self.parser_method_names)
        self.method_name_to_args = be.get_method_name_to_args()
        self.reset_root_dir()
    
    def parse(self, bql_string):
        ret_lines = []
        if len(bql_string) == 0:
            return
        bql_string = re.sub(r'--.*?\n', '', bql_string)
        lines = bql_string.split(';')
        for line in lines:
            if '--' in line:
                line = line[:line.index('--')]
            line = line.strip()
            if line is not None and len(line) > 0:
                ret_lines.append(line)
        return ret_lines
    
    def parse_line(self, bql_string):
        if len(bql_string) == 0:
            return
        if bql_string[-1] == ';':
            bql_string = bql_string[:-1]
        words = bql_string.lower().split()

        if len(words) >= 1 and words[0] == 'help':
            print "Welcome to BQL help. Here is a list of BQL commands and their syntax:\n"
            for method_name in sorted(self.method_names):
                help_method = getattr(self, 'help_' +  method_name)
                print help_method()
            return False

        for method_name in self.method_names:
            parse_method = getattr(self, 'parse_' + method_name)
            result = parse_method(words, bql_string)
            if result is None:
                continue
            elif result == False:
                return False
            elif result:
                return result

    def set_root_dir(self, root_dir):
        self.root_directory = root_dir

    def reset_root_dir(self):
        self.root_directory = os.getcwd()

    def get_absolute_path(self, relative_path):
        if os.path.isabs(relative_path):
            return relative_path
        else:
            return os.path.join(self.root_directory, relative_path)

    def help_start_from_scratch(self):
        return "START FROM SCRATCH: drop all btables."

    def parse_start_from_scratch(self, words, orig):
        if len(words) >= 3:
            if words[0] == 'start' and words[1] == 'from' and words[2] == 'scratch':
                return 'start_from_scratch', dict()

    def help_list_btables(self):
        return "LIST BTABLES: view the list of all btable names."

    def parse_list_btables(self, words, orig):
        if len(words) >= 2:
            if words[0] == 'list' and words[1] == 'btables':
                return 'list_btables', dict()

    def help_create_models(self):
        return "CREATE MODELS FOR <btable> [WITH <n_chains> EXPLANATIONS]: the step to perform before analyze."

    def parse_create_models(self, words, orig):
        n_chains = 10
        if len(words) >= 1:
            if words[0] == 'create' and (utils.is_int(words[1]) or words[1] == 'model' or words[1] == 'models'):
                if len(words) >= 4 and words[1] == 'model' or words[1] == 'models':
                    if words[2] == 'for':
                        tablename = words[3]
                        if len(words) >= 7:
                            if words[4] == 'with' and utils.is_int(words[5]) and words[6] == 'explanations':
                                n_chains = int(words[5])
                        result = 'create_models', dict(tablename=tablename, n_chains=n_chains)
                        print 'Created %d models for btable %s' % (n_chains, tablename)
                        return result
                    else:
                        print self.help_create_models()
                        return False
                elif len(words) >= 3 and utils.is_int(words[1]):
                    n_chains = int(words[1])
                    assert n_chains > 0
                    if words[2] == 'model' or words[2] == 'models':
                        if len(words) >= 5 and words[3] == 'for':
                            tablename = words[4]
                            result = 'create_models', dict(tablename=tablename, n_chains=n_chains)
                            print 'Created %d models for btable %s' % (n_chains, tablename)
                            return result
                        else:
                            print self.help_create_models()
                            return False
                else:
                    print self.help_create_models()
                    return False

    def help_create_btable(self):
        return "CREATE BTABLE <tablename> FROM <filename>: create a table from a csv file"

    def parse_create_btable(self, words, orig):
        crosscat_column_types = None
        if len(words) >= 2:
            if (words[0] == 'upload' or words[0] == 'create') and (words[1] == 'ptable' or words[1] == 'btable'):
                if len(words) >= 5:
                    tablename = words[2]
                    if words[3] == 'from':
                        f = open(self.get_absolute_path(orig.split()[4]), 'r')
                        csv = f.read()
                        result = ('create_btable',
                                 dict(tablename=tablename, csv=csv,
                                      crosscat_column_types=crosscat_column_types))
                        return result
                else:
                    print self.help_create_btable()
                    return False

    def help_drop_btable(self):
        return "DROP BTABLE <tablename>: drop table."

    def parse_drop_btable(self, words, orig):
        if len(words) >= 3:
            if words[0] == 'drop' and (words[1] == 'tablename' or words[1] == 'ptable' or words[1] == 'btable'):
                return 'drop_btable', dict(tablename=words[2])

    def help_delete_chain(self):
        return "DELETE CHAIN <chain_index> FROM <tablename>: delete the specified chain (model). chain_index may be 'all'."

    def parse_delete_chain(self, words, orig):
        if len(words) >= 3:
            if words[0] == 'delete':
                if words[1] == 'chain' and utils.is_int(words[2]):
                    chain_index = int(words[2])
                    if words[3] == 'from':
                        tablename = words[4]
                        return 'delete_chain', dict(tablename=tablename, chain_index=chain_index)
                elif len(words) >= 6 and words[2] == 'all' and words[3] == 'chains' and words[4] == 'from':
                    chain_index = 'all'
                    tablename = words[5]
                    return 'delete_chain', dict(tablename=tablename, chain_index=chain_index)
                else:
                    print self.help_delete_chain()
                    return False

    def help_analyze(self):
        return "ANALYZE <btable> [CHAIN INDEX <chain_index>] [FOR <iterations> ITERATIONS]: perform inference."

    def parse_analyze(self, words, orig):
        chain_index = 'all'
        iterations = 2
        wait = False
        if len(words) >= 1 and words[0] == 'analyze':
            if len(words) >= 2:
                tablename = words[1]
            else:
                print self.help_analyze()
                return False
            idx = 2
            if words[idx] == "chain" and words[idx+1] == 'index':
                chain_index = words[idx+2]
                idx += 3
            ## TODO: check length here
            if words[idx] == "for" and words[idx+2] == 'iterations':
                iterations = int(words[idx+1])
            return 'analyze', dict(tablename=tablename, chain_index=chain_index,
                                   iterations=iterations, wait=False)

    def help_infer(self):
        return "INFER col0, [col1, ...] FROM <btable> [WHERE <whereclause>] WITH CONFIDENCE <confidence> [LIMIT <limit>] [NUMSAMPLES <numsamples>] [ORDER BY SIMILARITY TO <row_id> [WITH RESPECT TO <column>]]: like select, but infers (fills in) missing values."
        
    def parse_infer(self, words, orig):
        match = re.search(r"""
            infer\s+
            (?P<columnstring>[^\s,]+(?:,\s*[^\s,]+)*)\s+
            from\s+(?P<btable>[^\s]+)\s+
            (where\s+(?P<whereclause>.*(?=with)))?
            \s*with\s+confidence\s+(?P<confidence>[^\s]+)
            (\s+limit\s+(?P<limit>[^\s]+))?
            (\s+numsamples\s+(?P<numsamples>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'infer':
                print self.help_infer()
                return False
            else:
                return None
        else:
            columnstring = match.group('columnstring').strip()
            tablename = match.group('btable')
            whereclause = match.group('whereclause')
            if whereclause is None:
                whereclause = ''
            else:
                whereclause = whereclause.strip()
            confidence = float(match.group('confidence'))
            limit = match.group('limit')
            if limit is None:
                limit = float("inf")
            else:
                limit = int(limit)
            numsamples = match.group('numsamples')
            if numsamples is None:
                numsamples = 1
            else:
                numsamples = int(numsamples)
            newtablename = '' # For INTO
            orig, order_by = self.extract_order_by(orig)
            return 'infer', dict(tablename=tablename, columnstring=columnstring, newtablename=newtablename,
                                 confidence=confidence, whereclause=whereclause, limit=limit,
                                 numsamples=numsamples, order_by=order_by)


    def extract_order_by(self, orig):
        pattern = r"""
            (order\s+by\s+(?P<orderbyclause>.*?((?=limit)|$)))
        """ 
        match = re.search(pattern, orig, re.VERBOSE | re.IGNORECASE)
        if match:
            order_by_clause = match.group('orderbyclause')
            ret = list()
            orderables = list()
            for orderable in utils.column_string_splitter(order_by_clause):
                ## Check for DESC
                desc = re.search(r'\s+desc($|\s|,|(?=limit))', orderable, re.IGNORECASE)
                orderable = re.sub(r'\s+desc($|\s|,|(?=limit))', '', orderable, re.IGNORECASE)
                ## Check for similarity
                pattern = r"""
                    similarity\s+to\s+(?P<rowid>[^\s]+)
                    (\s+with\s+respect\s+to\s+(?P<column>[^\s]+))?
                """
                match = re.search(pattern, orderable, re.VERBOSE | re.IGNORECASE)
                if match:
                    rowid = int(match.group('rowid').strip())
                    if match.group('column'):
                        column = match.group('column').strip()
                    else:
                        column = None
                    orderables.append(('similarity', {'desc': desc, 'target_row_id': rowid, 'target_column': column}))
                else:
                    match = re.search(r"""
                          similarity_to\s*\(\s*
                          (?P<rowid>[^,]+)
                          (\s*,\s*(?P<column>[^\s]+)\s*)?
                          \s*\)
                      """, orderable, re.VERBOSE | re.IGNORECASE) 
                    if match:
                        if match.group('column'):
                            column = match.group('column').strip()
                        else:
                            column = None
                        rowid = match.group('rowid').strip()
                        if utils.is_int(rowid):
                            target_row_id = int(rowid)
                        else:
                            target_row_id = rowid
                        orderables.append(('similarity', {'desc': desc, 'target_row_id': target_row_id, 'target_column': column}))

                    else:
                        orderables.append(('column', {'desc': desc, 'column': orderable.strip()}))
            orig = re.sub(pattern, '', orig, flags=re.VERBOSE | re.IGNORECASE)
            return (orig, orderables)
        else:
            return (orig, False)



    def extract_limit(self, orig):
        pattern = r'limit\s+(?P<limit>\d+)'
        match = re.search(pattern, orig.lower())
        if match:
            limit = int(match.group('limit').strip())
            return limit
        else:
            return float('inf')

    def help_export_samples(self):
        return "EXPORT SAMPLES FROM <btable> TO <pklpath>: export your samples (aka models, chains) to a pickle file."

    def parse_export_samples(self, words, orig):
        match = re.search(r"""
            export\s+
            (samples\s+)?
            from\s+
            (?P<btable>[^\s]+)
            \s+to\s+
            (?P<pklpath>[^\s]+)
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'export':
                print self.help_export_samples()
                return False
            else:
                return None
        else:
            tablename = match.group('btable')
            pklpath = match.group('pklpath')
            if pklpath[-7:] != '.pkl.gz':
                pklpath = pklpath + ".pkl.gz"
            return 'export_samples', dict(tablename=tablename, pkl_path=pklpath)

    def help_import_samples(self):
        return "IMPORT SAMPLES <pklpath> INTO <btable> [ITERATIONS <iterations>]: import samples from a pickle file."

    def parse_import_samples(self, words, orig):
        match = re.search(r"""
            import\s+
            (samples\s+)?
            (?P<pklpath>[^\s]+)\s+
            into\s+
            (?P<btable>[^\s]+)
            (\s+iterations\s+(?P<iterations>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'import':
                print self.help_import_samples()
                return False
            else:
                return None
        else:
            tablename = match.group('btable')
            pklpath = match.group('pklpath')
            if pklpath[-3:] == '.gz':
                samples = pickle.load(gzip.open(self.get_absolute_path(pklpath), 'rb'))
            else:
                samples = pickle.load(open(self.get_absolute_path(pklpath), 'rb'))
            X_L_list = samples['X_L_list']
            X_D_list = samples['X_D_list']
            M_c = samples['M_c']
            T = samples['T']
            if match.group('iterations'):
                iterations = int(match.group('iterations').strip())
            else:
                iterations = 0
            return 'import_samples', dict(tablename=tablename, X_L_list=X_L_list, X_D_list=X_D_list,
                                          M_c=M_c, T=T, iterations=iterations)

    def help_select(self):
        return 'SELECT col0, [col1, ...] FROM <btable> [WHERE <whereclause>] '+\
            '[ORDER BY SIMILARITY TO <rowid> [WITH RESPECT TO <column>]] [LIMIT <limit>]: like SQL select.'
        
    def parse_select(self, words, orig):
        match = re.search(r"""
            select\s+
            (?P<columnstring>.*?((?=from)))
            \s*from\s+(?P<btable>[^\s]+)\s*
            (where\s+(?P<whereclause>.*?((?=limit)|(?=order)|$)))?
            (\s*limit\s+(?P<limit>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'select':
                print self.help_select()
                return False
            else:
                return None
        else:
            columnstring = match.group('columnstring').strip()
            tablename = match.group('btable')
            whereclause = match.group('whereclause')
            if whereclause is None:
                whereclause = ''
            else:
                whereclause = whereclause.strip()
            limit = self.extract_limit(orig)
            orig, order_by = self.extract_order_by(orig)
            return 'select', dict(tablename=tablename, columnstring=columnstring, whereclause=whereclause,
                                  limit=limit, order_by=order_by)

    def help_simulate(self):
        return "SIMULATE col0, [col1, ...] FROM <btable> [WHERE <whereclause>] TIMES <times> [ORDER BY SIMILARITY TO <row_id> [WITH RESPECT TO <column>]]: simulate new datapoints based on the underlying model."

    def parse_simulate(self, words, orig):
        match = re.search(r"""
            simulate\s+
            (?P<columnstring>[^\s,]+(?:,\s*[^\s,]+)*)\s+
            from\s+(?P<btable>[^\s]+)\s+
            (where\s+(?P<whereclause>.*(?=times)))?
            times\s+(?P<times>[^\s]+)
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'simulate':
                print self.help_simulate()
                return False
            else:
                return None
        else:
            columnstring = match.group('columnstring').strip()
            tablename = match.group('btable')
            whereclause = match.group('whereclause')
            if whereclause is None:
                whereclause = ''
            else:
                whereclause = whereclause.strip()
            numpredictions = int(match.group('times'))
            newtablename = '' # For INTO
            orig, order_by = self.extract_order_by(orig)
            return 'simulate', dict(tablename=tablename, columnstring=columnstring, newtablename=newtablename,
                                    whereclause=whereclause, numpredictions=numpredictions, order_by=order_by)

    def help_estimate_dependence_probabilities(self):
        return "ESTIMATE DEPENDENCE PROBABILITIES FROM <btable> [[REFERENCING <col>] [WITH CONFIDENCE <prob>] [LIMIT <k>]] [SAVE TO <file>]: get probabilities of column dependence."

    def parse_estimate_dependence_probabilities(self, words, orig):
        match = re.search(r"""
            estimate\s+dependence\s+probabilities\s+from\s+
            (?P<btable>[^\s]+)
            ((\s+referencing\s+(?P<refcol>[^\s]+))|(\s+for\s+(?P<forcol>[^\s]+)))?
            (\s+with\s+confidence\s+(?P<confidence>[^\s]+))?
            (\s+limit\s+(?P<limit>[^\s]+))?
            (\s+save\s+to\s+(?P<filename>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'estimate':
                print self.help_estimate_dependence_probabilities()
                return False
            else:
                return None
        else:
            tablename = match.group('btable').strip()
            if match.group('refcol'):
                col = match.group('refcol')
                submatrix = True
            else:
                col = match.group('forcol')
                submatrix = False
            confidence = match.group('confidence')
            if match.group('limit'):
                limit = int(match.group('limit'))
            else:
                limit = float("inf")
            if match.group('filename'):
                filename = match.group('filename')
            else:
                filename = None
            return 'estimate_dependence_probabilities', dict(tablename=tablename, col=col, confidence=confidence,
                                                             limit=limit, filename=filename, submatrix=submatrix)

    def extract_columns(self, orig):
        """TODO"""
        pattern = r"""
            \(\s*
            (estimate\s+)?
            columns\s+where\s+
            (?P<columnstring>\d+
            \)
        """
        match = re.search(pattern, orig.lower(), re.VERBOSE | re.IGNORECASE)
        if match:
            limit = int(match.group('limit').strip())
            return limit
        else:
            return float('inf')

    def help_estimate_pairwise(self):
        return "ESTIMATE PAIRWISE [DEPENDENCE PROBABILITY | CORRELATION | MUTUAL INFORMATION] FROM <btable> [SAVE TO <file>]: estimate a pairwise function of columns."
        
    def parse_estimate_pairwise(self, words, orig):
        match = re.search(r"""
            estimate\s+pairwise\s+
            (?P<functionname>.*?((?=\sfrom)))
            \s*from\s+
            (?P<btable>[^\s]+)
            (\s+save\s+to\s+(?P<filename>[^\s]+))?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'estimate' and words[1] == 'pairwise':
                print self.help_estimate_pairwise()
                return False
            else:
                return None
        else:
            tablename = match.group('btable').strip()
            function_name = match.group('functionname').strip().lower()
            if function_name not in ["mutual information", "correlation", "dependence probability"]:
                print 'Did you mean: ESTIMATE PAIRWISE [DEPENDENCE PROBABILITY | CORRELATION | MUTUAL INFORMATION] FROM <btable> [SAVE TO <file>]'
                return False
            if match.group('filename'):
                filename = match.group('filename')
            else:
                filename = None
            return 'estimate_pairwise', dict(tablename=tablename, function_name=function_name, filename=filename)

    def help_update_datatypes(self):
        return "UPDATE DATATYPES FROM <btable> SET [col0=numerical|categorical|key|ignore]: must be done before creating models or analyzing."
        
    def parse_update_datatypes(self, words, orig):
        match = re.search(r"""
            update\s+datatypes\s+from\s+
            (?P<btable>[^\s]+)\s+
            set\s+(?P<mappings>[^;]*);?
        """, orig, re.VERBOSE | re.IGNORECASE)
        if match is None:
            if words[0] == 'update':
                print self.help_update_datatypes()
                return False
            else:
                return None
        else:
            tablename = match.group('btable').strip()
            mapping_string = match.group('mappings').strip()
            mappings = dict()
            for mapping in mapping_string.split(','):
                vals = mapping.split('=')
                if 'continuous' in vals[1] or 'numerical' in vals[1]:
                    datatype = 'continuous'
                elif 'multinomial' in vals[1] or 'categorical' in vals[1]:
                    m = re.search(r'\((?P<num>[^\)]+)\)', vals[1])
                    if m:
                        datatype = int(m.group('num'))
                    else:
                        datatype = 'multinomial'
                elif 'key' in vals[1]:
                    datatype = 'key'
                elif 'ignore' in vals[1]:
                    datatype = 'ignore'
                else:
                    print self.help_update_datatypes()
                    return False
                mappings[vals[0]] = datatype
            return 'update_datatypes', dict(tablename=tablename, mappings=mappings)

