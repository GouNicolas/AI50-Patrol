def choisir_destination(self, agents, TEMPS_SIMULATION):
    meilleur_noeud = None
    meilleure_liaison = None
    meilleur_score = -float("inf")

    for liaison in self.noeud_actuel.liaisons:
        voisin = liaison.cible
        poids = liaison.poids

        # scor du poids
        score_poids = 1.0 / (poids + 1e-5)

        # temps ecoule
        score_temps = voisin.temps_non_visite / TEMPS_SIMULATION

        # penalite otre agent
        penalite = sum(
            0.5 for a in agents
            if a != self and a.destination == voisin
        )

        poids_arete, poids_temps = 0.5, 10.0
        score = (poids_arete * score_poids) + (poids_temps * score_temps) - penalite

        if score > meilleur_score:
            meilleur_score = score
            meilleur_noeud = voisin
            meilleure_liaison = liaison

    if meilleure_liaison:
        self.destination = meilleur_noeud
        self.noeud_depart_trajet = self.noeud_actuel
        self.temps_trajet_total = meilleure_liaison.poids / self.vitesse
        self.temps_trajet_ecoule = 0.0
