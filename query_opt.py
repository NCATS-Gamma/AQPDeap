import random

from deap import base
from deap import creator
from deap import tools

from neo import graphdb
from ealgorithms import modeaMuPlusLambda
from operators import Mutator,Evaluator,graph_mate

import networkx as nx
import numpy
 

class Query:
    qi = 1
    def __init__(self,a,b):
        self.a = a
        self.b = b
        self.i = Query.qi
        Query.qi += 1
        self.graph = nx.Graph()
        self.add_node(a)
        self.add_node(b)
        self.next_node = 0
    def add_node(self,n):
        self.graph.add_node(n[0],ntype=n[1])
    def get_cypher(self,b_id,max_conn=1000):
        cypher = 'MATCH '
        edge_matches = [f'({s}:{self.graph.nodes[s]["ntype"]})-[:{d["edge_type"]}]-({t}:{self.graph.nodes[t]["ntype"]})'
                        for s,t,d in self.graph.edges(data=True)]
        cypher += ','.join(edge_matches)
        cypher += f' WHERE b.id="{b_id}"'
        if max_conn > 0:
            for node in self.graph.nodes():
                if node != 'a' and node != 'b':
                    cypher += f' AND size(({node})-[]-()) < {max_conn}'
        cypher += ' RETURN distinct a.id'
        return cypher
    def __repr__(self):
        return self.get_cypher('b_id')

def createQuery(cls,m,a,b):
    q = cls(a,b)
    print(f"New Query {q.qi}")
    for i in range(random.randint(1,2)):
        print( " new path")
        m.add_path(q,nhopdist=[1,1,1,2,2,3,4],start_node='a',end_node='b')
    return q

def run_algorithm():
    NGEN = 50
    MU = 50
    LAMBDA = 100
    CXPB = 0.2
    MUTPB = 0.7

    b_id = 'MONDO:0005148'
    predicate = 'treats'
    neo = graphdb()

    node_types = neo.get_node_types()
    edge_types = neo.get_edge_types(node_types)
    mutator = Mutator(node_types,edge_types,predicate)
    evaluator = Evaluator(f'(a:chemical_substance)-[:{predicate}]-(b:disease {{id:"{b_id}"}})',neo,b_id)

    creator.create("RecallPrecision", base.Fitness, weights=(1.0,1.0))
    creator.create("Individual", Query, fitness=creator.RecallPrecision)

    toolbox = base.Toolbox()
    #the individual creator gets a handle to the mutator so that it can use the generate path functionality
    toolbox.register("individual",createQuery,creator.Individual,mutator,('a','chemical_substance'),('b','disease'))
    toolbox.register("population", tools.initRepeat, list, toolbox.individual)
    toolbox.register("mate", graph_mate)
    toolbox.register("mutate", mutator.graph_mutate )
    toolbox.register("select", tools.selTournament, tournsize=3)
    toolbox.register("evaluate", evaluator.evaluate)

    print("Create population")
    pop = toolbox.population(n=MU)

    print("Create HOF")
    hof = tools.ParetoFront()
    stats = tools.Statistics(lambda ind: ind.fitness.values)
    stats.register("avg", numpy.mean, axis=0)
    stats.register("std", numpy.std, axis=0)
    stats.register("min", numpy.min, axis=0)
    stats.register("max", numpy.max, axis=0)

    logbook = tools.Logbook()
    logbook.header = "gen","evals","std","min","avg","max"


    # Evaluate the individuals with an invalid fitness
    #invalid_ind = [ind for ind in pop if not ind.fitness.valid]
    print("Evaluate Fitnesses")
    fitnesses = toolbox.map(toolbox.evaluate, pop)
    for ind, fit in zip(pop, fitnesses):
        ind.fitness.values = fit

    # This is just to assign the crowding distance to the individuals
    # no actual selection is done
    pop = toolbox.select(pop, len(pop))

    with open('HOF_queries_MONDO_0005148','w') as outfile:
        modeaMuPlusLambda(pop, toolbox, MU, LAMBDA, CXPB, MUTPB, NGEN, stats=stats,outf=outfile, halloffame=hof)


    #return pop, stats, hof

if __name__ == '__main__':
    run_algorithm()
