import random
import networkx as nx
from collections import defaultdict
from copy import deepcopy

class Mutator:

    def __init__(self,node_types,edge_types,tp):
        self.node_types = node_types
        self.edge_types = edge_types
        self.target_predicate = tp

    def choose_random_node_type(self,censored_types):
        new_type = None
        while new_type is not None or new_type in censored_types:
            new_type = random.choice(self.node_types)
        return new_type

    def choose_random_edge_type(self,node_type_a,node_type_b):
        k=(node_type_a,node_type_b)
        if k not in self.edge_types:
            return None
        return random.choice(self.edge_types[k])

    def update_edge_types(self,graph,node):
        """Check all edges for a node and assign them an allowed type. If a type cannot be allowed, delete the edge"""
        edges = graph.edges(node,data=True)
        toremove = []
        for (s,t,d) in edges:
            etype = self.choose_random_edge_type(graph.nodes[s]['ntype'],graph.nodes[t]['ntype'])
            if etype is None:
                toremove.append( (s,t) )
            else:
                d['edge_type'] = etype
        for s,t in toremove:
            graph.remove_edge(s,t)

    def prune(self,query):
        graph = query.graph
        while True:
            danglers = [node for (node, val) in graph.degree() if val < 2]
            if 'a' in danglers:
                danglers.remove('a')
            if 'b' in danglers:
                danglers.remove('b')
            for d in danglers:
                graph.remove_node(d)
            if len(danglers)==0:
                break

    def accepts(self,query):
        """Is the query that remains from all this fooling around valid?"""
        #Are all the nodes right?
        for n in  query.graph.nodes():
            if n == 'a':
                continue
            elif n=='b':
                continue
            elif not n.startswith('n'):
                print('I cant accept this!')
                print(n)
                exit()
        #The target link is not in the query
        if query.graph.has_edge('a','b'):
            if self.target_predicate == query.graph.edges['a','b']['edge_type']:
                return False
        #There is at least one path from a to b and all nodes are on at least one path from a to b.
        paths = nx.all_simple_paths(query.graph,'a','b')
        at_least_one = False
        pathed_nodes = set()
        for p in paths:
            at_least_one = True
            pathed_nodes.update(p)
        if not at_least_one:
            return False
        all_nodes = set(query.graph.nodes())
        unpathed_nodes = all_nodes.difference(pathed_nodes)
        return len(unpathed_nodes) == 0


    def graph_mutate(self,query):
        #sometimes a mutator will fail (mutate into an invalid query).
        while True:
            i_query = deepcopy(query)
            mutators = [self.mutate_node_type,
                        self.mutate_edge_type,
                        self.add_edge,
                        self.remove_edge,
                        self.add_path,
                        self.remove_node]
            m = random.choice(mutators)
            m_query, success= m(i_query)
            if not success:
                continue
            self.prune(m_query)
            if self.accepts(m_query):
                return m_query,

    def mutate_node_type(self,query):
        graph = query.graph
        nodes = list(graph.nodes())
        nodes.remove('a')
        nodes.remove('b')
        if len(nodes) == 0:
            #No nodes to mutate
            return query,False
        mnode = random.choice(nodes)
        new_type = self.choose_random_node_type([graph.nodes[mnode]['ntype']])
        graph.nodes[mnode]['ntype']=new_type
        self.update_edge_types(graph,mnode)
        return query,True

    def mutate_edge_type(self,query):
        graph = query.graph
        edges = list(graph.edges(data=True))
        if len(edges) == 0:
            return query,False
        s,t,d = random.choice(edges)
        new_type = self.choose_random_edge_type(graph.nodes[s]['ntype'],graph.nodes[t]['ntype'])
        d['edge_type'] = new_type
        return query,True

    def add_edge(self,query):
        """Choose two nodes at random and put an edge between them"""
        graph = query.graph
        all_nodes = set(graph.nodes())
        node1 = random.choice(list(all_nodes))
        connected = set(graph.edges(node1))
        unconnected = all_nodes.difference(connected)
        if len(unconnected) == 0:
            return query,False
        node2 = random.choice(list(unconnected))
        new_type = self.choose_random_edge_type(graph.nodes[node1]['ntype'],graph.nodes[node2]['ntype'])
        if new_type is None:
            return query,False
        graph.add_edge(node1,node2,edge_type=new_type)
        return query,True

    def remove_edge(self,query):
        the_edges = list(query.graph.edges())
        if len(the_edges) == 0:
            return query,False
        random_edge = random.choice(the_edges)
        query.graph.remove_edge(*random_edge)
        return query,True

    #Add node/edge is a subset of this
    def add_path(self,query,nhopdist=[1,1,1,1,1,1,2,2,2,2,3,3,4],start_node=None,end_node=None):
        graph = query.graph
        if start_node is None:
            start_node = random.choice(list(graph.nodes()))
        if end_node is None:
            end_node = start_node
            while end_node == start_node:
                end_node = random.choice(list(graph.nodes()))
        connected = False
        if graph.has_edge(start_node,end_node):
            connected = True
        #This is dumb, but we first generate a sequence of types and try to connect them.  if we can't
        # then we try again with a new sequence of types etc.
        nhops = random.choice(nhopdist)
        if connected and nhops == 1:
            #we already have an edge from start to end, so adding nhop=1 does nothing, make it nhop=2
            nhops = 2
        while True:
            pathnodes=[(start_node,graph.nodes[start_node]['ntype'])]
            for i in range(nhops):
                n = (f'n{query.next_node}', random.choice(self.node_types))
                pathnodes.append(n)
                query.next_node += 1
            pathnodes.append( (end_node,graph.nodes[end_node]['ntype']) )
            es = []
            for i in range(len(pathnodes)-1):
                source=pathnodes[i]
                target=pathnodes[i+1]
                try:
                    etype = random.choice(self.edge_types[ (source[1],target[1]) ])
                    es.append( (source[0],target[0],etype) )
                except Exception as e:
                    continue
                    #print(f'No edges connecting {source[1]} and {target[1]}')
            if len(es) == len(pathnodes)-1:
                for n in pathnodes:
                    #print(f"   Add node {n}")
                    query.add_node(n)
                for s,t,e in es:
                    #print(f"   Add edge {s}-{t}")
                    graph.add_edge(s,t,edge_type=e)
                break
        #Now, we've connected start and end.  If they were already connected, do we want to replace the edge or
        # augment it?  Flip for it.
        if connected and random.random() < 0.5:
            #print(f"   Remove edge {start_node}-{end_node}")
            graph.remove_edge(start_node,end_node)
            self.prune(query)
        return query,True

    #This may remove a whole path because it culls dangling nodes.
    # or does it?  There maybe be an argument that queries with extra nodes hanging off represent extra constraints on
    # a node.  I think not for the moment, but it would simplify a lot of these mutations.  I mean, if you really went down
    # this rabbit hole, you might not even need for the a node to be connected to the b node, but just to have a set
    # of local enviromental properties that indicate that it should be connected.
    def remove_node(self,query):
        nodes = set(query.graph.nodes())
        nodes.remove('a')
        nodes.remove('b')
        if len(nodes) == 0:
            return query,False
        d_node = random.choice(list(nodes))
        query.graph.remove_node(d_node)
        return query,True

    def merge_nodes(self,query):
        nodesbytype = defaultdict(list)
        for node in query.graph.nodes():
            if node not in ('a','b'):
                nodesbytype[ query.graph.nodes[node]['ntype']].append(node)
        nodesbytype_filtered = {k:v for k,v in nodesbytype.items() if len(v) > 1}
        #pick a type, then pick 2 nodes from that type
        ntype = random.choice(nodesbytype_filtered.keys())
        nodes_to_merge = nodesbytype_filtered[ntype]
        query.graph = nx.contracted_nodes(query.graph,nodes_to_merge[0],nodes_to_merge[1],self_loops=False)
        return query,True

def graph_mate(oquery1, oquery2):
    """Simply combine the two queries with an AND.  there may be more interesting ways to try to overlap them..."""
    #We have to be a little careful here, because we might have two nodes with the same name in the two queries, but
    # they're not the same because they have different types....
    #print("MATING")
    query1 = deepcopy(oquery1)
    query2 = deepcopy(oquery2)
    nodenames={'a':'a', 'b':'b'}
    for node in query2.graph.nodes():
        if node not in ('a','b'):
            nodenames[node]=f'n{query1.next_node}'
            query1.graph.add_node(f'n{query1.next_node}', ntype=query2.graph.nodes[node]['ntype'])
            query1.next_node += 1
    for n1,n2,d in query2.graph.edges(data=True):
        try:
            query1.graph.add_edge(nodenames[n1],nodenames[n2],edge_type=d['edge_type'])
        except:
            print('Failed transferring edge')
            print(query2.get_cypher('b.id'))
            print(n1,n2)
            print(d)
            exit()
    #print("   MATED")
    return query1,query2

class Evaluator:
    def __init__(self,pedge,neo,b_curie):
        self.neo = neo
        self.predict_edge = pedge
        self.true_positives = neo.get_all_true_positives(pedge)
        self.tp_count = len(self.true_positives)
        self.b_id = b_curie
    def evaluate(self,q):
        #print(f'EVALUATING ')
        #print(q.get_cypher(self.b_id))
        results = set(self.neo.get_matches(q.get_cypher(self.b_id)))
        hits = results.intersection(self.true_positives)
        recall = len(hits)/self.tp_count
        if len(results) == 0:
            precision = 0
        else:
            precision = len(hits) / len(results)
        #print(recall,precision)
        return recall,precision

