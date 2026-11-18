# CTAP minimal (ctap.py)
# Dans test IA50.py : from ctap import choisir_destination

import heapq
import itertools
import random

_clusters = {}    # agent.id -> liste des noeuds de son territoire
_agent_ids = frozenset()
_cpt = itertools.count()
EXECUTION_KMEANS = 10

def _dijkstra(depart, but):
    # plus court chemin, renvoie le PREMIER noeud a rejoindre (un saut)
    if depart is None or but is None:
        return None
    if depart.id == but.id:
        return None

    prec = {}
    dist = {depart.id: 0}
    file = [(0, next(_cpt), depart)]
    while file:
        d, _, n = heapq.heappop(file)
        if d > dist.get(n.id, float("inf")):
            continue
        if n.id == but.id:
            chemin = [but]
            while chemin[-1].id != depart.id:
                chemin.append(prec[chemin[-1].id])
            return chemin[-2]
        for l in n.liaisons:
            nouvelle_distance = d + l.poids
            ancienne_distance = dist.get(l.cible.id, float("inf"))
            if nouvelle_distance < ancienne_distance:
                dist[l.cible.id] = nouvelle_distance
                prec[l.cible.id] = n
                element = (nouvelle_distance, next(_cpt), l.cible)
                heapq.heappush(file, element)
    return None


def _init(agents):
    # fission : partition k-means des noeuds, un territoire par agent (leader)
    vus = set()
    file = [a.noeud_actuel for a in agents]
    noeuds = []
    while file:
        n = file.pop()
        if n not in vus:
            vus.add(n)
            noeuds.append(n)
            voisins = [liaison.cible for liaison in n.liaisons]
            file += voisins

    nombre_centres = min(len(agents), len(noeuds))
    centres_aleatoires = random.sample(noeuds, nombre_centres)
    centres = [(n.x, n.y) for n in centres_aleatoires]
    for _ in range(EXECUTION_KMEANS):
        assign = {}
        for n in noeuds:
            distances = []
            for i in range(len(centres)):
                distance = ((n.x - centres[i][0]) ** 2
                            + (n.y - centres[i][1]) ** 2)
                distances.append(distance)
            centre_le_plus_proche = min(range(len(centres)),
                                        key=lambda i: distances[i])
            assign[n.id] = centre_le_plus_proche

        nouveau = []
        for i in range(len(centres)):
            g = [n for n in noeuds if assign[n.id] == i]
            if g:
                moyenne_x = sum(n.x for n in g) / len(g)
                moyenne_y = sum(n.y for n in g) / len(g)
                nouveau.append((moyenne_x, moyenne_y))
            else:
                nouveau.append(centres[i])
        centres = nouveau
    for i, a in enumerate(agents):
        _clusters[a.id] = [n for n in noeuds if assign[n.id] == i % len(centres)]


def choisir_destination(self, agents, TEMPS_SIMULATION):
    global _agent_ids

    current_ids = frozenset(a.id for a in agents)

    if _agent_ids != current_ids:
        _init(agents)
        _agent_ids = current_ids
    # patrouille : le leader vise le noeud le plus detendu de son territoire
    reserve = set()
    for agent in agents:
        if agent is not self and agent.destination:
            reserve.add(agent.destination.id)

    curseur = self.noeud_actuel
    if curseur is None:
        self.destination = None
        return

    noeuds_disponibles = []
    for noeud in _clusters[self.id]:
        if noeud.id not in reserve:
            noeuds_disponibles.append(noeud)

    if noeuds_disponibles:
        but = max(noeuds_disponibles, key=lambda n: n.temps_non_visite)
    else:
        but = None

    if but is None or but is curseur:
        if not curseur.liaisons:
            self.destination = None
            return
        cible = random.choice(curseur.liaisons).cible
    else:
        cible = _dijkstra(curseur, but)

    if cible is None:
        self.destination = None
        return

    liaison = next(
        (l for l in curseur.liaisons if l.cible.id == cible.id),
        None
    )
    if liaison is None:
        self.destination = None
        return

    self.destination, self.noeud_depart_trajet = cible, curseur
    self.temps_trajet_total = liaison.poids / self.vitesse
    self.temps_trajet_ecoule = 0.0