import random

def choisir_destination(self, agents, TEMPS_SIMULATION):

    # choi au pif du voisin
    liaison = random.choice(self.noeud_actuel.liaisons)

    self.destination = liaison.cible
    self.noeud_depart_trajet = self.noeud_actuel

    # calc du temps de trajet
    self.temps_trajet_total = liaison.poids / self.vitesse
    self.temps_trajet_ecoule = 0.0









