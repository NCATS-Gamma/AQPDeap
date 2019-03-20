from neo4j import GraphDatabase,unit_of_work
import os
import time

@unit_of_work(timeout=300)
def runcypher(tx,cypher):
    return tx.run(cypher)

class graphdb:

    def __init__(self):
        url = 'bolt://robokopdev.renci.org:7687'
        self.driver = GraphDatabase.driver(url, auth=("neo4j", os.environ['NEO4J_PASSWORD']))

    def run_query(self,cypherquery):
        start = time.time()
        print('Start query:',cypherquery)
        try:
            with self.driver.session() as session:
                #results = session.run(Statement(cypherquery,timeout=300))
                #results = session.run(cypherquery,timeout=.1,wtf=123)
                results = session.read_transaction(runcypher,cypherquery)
            end = time.time()
            print(f'Done. Ran for {end-start}')
            lr = list(results)
            return lr
        except:
            print('Timeout')
            return [] 

    def get_node_types(self):
        node_type_set = set()
        nodequery = 'MATCH (n) RETURN DISTINCT LABELS(n) AS l'
        node_results = self.run_query(nodequery)
        for node_result in node_results:
            nr = node_result['l']
            if 'named_thing' in nr:
                node_type_set.update(nr)
        node_types = list(node_type_set)
        node_types.remove('named_thing')
        node_types.remove('Concept')
        node_types.sort()
        print(f"Found {len(node_types)} node_types")
        return node_types

    def get_edge_types(self,node_types):
        bads = [ 'is_a','mereotopologically_related_to','Unmapped_Relation', 'contributes_to' ]
        edge_types = {}
        for i,nt0 in enumerate(node_types):
            for nt1 in node_types[i:]:
                k = (nt0,nt1)
                rk = (nt1,nt0)
                equery = f'MATCH (a:{nt0})-[x]-(b:{nt1}) WHERE not a:Concept and not b:Concept RETURN DISTINCT TYPE(x) as etype'
                edge_results = self.run_query(equery)
                et = [r['etype'] for r in edge_results]
                for bad in bads:
                    if bad in et:
                        et.remove(bad)
                if len(et) > 0:
                    edge_types[k] = et
                    edge_types[rk] = et
#        for p,v in edge_types.items():
#            print(p, len(v))
        print(f"Found {len(edge_types)} edge_types")
        return edge_types

    def get_all_true_positives(self,target_link):
        linkcypher = f"MATCH p = {target_link} return distinct a.id"
        positives = [r['a.id'] for r in list(self.run_query(linkcypher))]
        print(f"Found {len(positives)} positive examples")
        return positives

    def get_matches(self,cypher):
        return [r['a.id'] for r in list(self.run_query(cypher))]
