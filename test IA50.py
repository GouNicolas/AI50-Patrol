import math
import random
import pygame
import xml.etree.ElementTree as ET
from tkinter import Tk, filedialog, simpledialog

import os
import glob
import importlib.util

from choix import choisir_destination

# config de la simu
LARGEUR, HAUTEUR = 1000, 700
NB_NOEUDS = 100
NB_AGENTS = 10

DIST_MAX_LIAISON = 200 # dist max sur la carte pr connecter 2 noeuds
MAX_VOISINS = 4 # nb max de voisin par noeud
AFFICHER_LIAISONS = True

RAYON_NOEUD = 10
RAYON_AGENT = 8
FPS = 120

TEMPS_SIMULATION = 50 # en sec
TEMPS_MAX = 10 # temps pr passer du vert au rouge

VITESSE_AGENTS = 10


class Liaison:
    def __init__(self, noeud_cible, poids):
        self.cible = noeud_cible
        self.poids = poids


class Noeud:
    def __init__(self, id, x, y):
        self.id = id
        self.x = x
        self.y = y
        self.temps_non_visite = 0
        self.temps_visites = []
        self.liaisons = []

    def position(self):
        return self.x, self.y


class Agent:
    def __init__(self, id, noeud_depart):
        self.id = id
        self.noeud_actuel = noeud_depart
        self.destination = None
        self.x = noeud_depart.x
        self.y = noeud_depart.y
        self.vitesse = 10

        self.temps_trajet_total = 0
        self.temps_trajet_ecoule = 0
        self.noeud_depart_trajet = noeud_depart

        self.noeud_actuel.temps_non_visite = 0

    def avancer(self, dt):
        if self.destination is None:
            return

        self.temps_trajet_ecoule += dt
        ratio = min(self.temps_trajet_ecoule / self.temps_trajet_total, 1.0)

        # deplacement visuel
        self.x = self.noeud_depart_trajet.x + (self.destination.x - self.noeud_depart_trajet.x) * ratio
        self.y = self.noeud_depart_trajet.y + (self.destination.y - self.noeud_depart_trajet.y) * ratio

        if ratio >= 1.0:
            self.x, self.y = self.destination.x, self.destination.y
            self.noeud_actuel = self.destination

            self.noeud_actuel.temps_visites.append(self.noeud_actuel.temps_non_visite)
            self.noeud_actuel.temps_non_visite = 0
            self.destination = None


def choisir_fichier_graphe():
    fenetre = Tk()
    fenetre.withdraw()

    chemin = filedialog.askopenfilename(
        title="ouvrir un graphe",
        filetypes=[
            ("fichiers graph", "*.graph"),
            ("tous les fichiers", "*.*")
        ]
    )

    fenetre.destroy()
    return chemin


def ouvrir_graphe(chemin):
    arbre = ET.parse(chemin)
    racine = arbre.getroot()

    element_noeuds = racine.find("Nodes")

    Positions = []

    for element in element_noeuds.findall("Node"):
        position = element.get("Position")

        valeurs = [float(v.strip()) for v in position.split(",")]

        x, y, z = valeurs
        Positions.append((x, y, z))

    xs = [p[0] for p in Positions]
    zs = [p[2] for p in Positions]

    min_x, max_x = min(xs), max(xs)
    min_z, max_z = min(zs), max(zs)

    marge = 80
    largeur_utile = LARGEUR - 2 * marge
    hauteur_utile = HAUTEUR - 2 * marge

    Noeuds = []

    for i, (x, y, z) in enumerate(Positions):
        if max_x == min_x:
            px = LARGEUR / 2
        else:
            px = marge + (x - min_x) / (max_x - min_x) * largeur_utile

        if max_z == min_z:
            py = HAUTEUR / 2
        else:
            py = HAUTEUR - marge - (
                (z - min_z) / (max_z - min_z) * hauteur_utile
            )

        Noeuds.append(Noeud(i, int(px), int(py)))

    element_liaisons = racine.find("Edges")

    if element_liaisons is not None:
        for element in element_liaisons.findall("Edge"):
            indices = element.get("Indices")

            valeurs = [int(v.strip()) for v in indices.split(",")]

            i, j = valeurs

            poids = math.dist(Positions[i], Positions[j])
            poids = max(poids, 0.001)

            Noeuds[i].liaisons.append(Liaison(Noeuds[j], poids))
            Noeuds[j].liaisons.append(Liaison(Noeuds[i], poids))

    Poids_liaisons = [
        liaison.poids
        for noeud in Noeuds
        for liaison in noeud.liaisons
    ]

    if Poids_liaisons:
        poids_moyen = sum(Poids_liaisons) / len(Poids_liaisons)
        global VITESSE_AGENTS
        VITESSE_AGENTS = 4.0 * poids_moyen
    else:
        VITESSE_AGENTS = 0.1

    return Noeuds


def distance(n1, n2):
    return math.dist((n1.x, n1.y), (n2.x, n2.y))


def creer_graphe(nb_noeuds):
    Noeuds = []
    for i in range(nb_noeuds):
        x = random.randint(80, LARGEUR - 80)
        y = random.randint(80, HAUTEUR - 80)
        Noeuds.append(Noeud(i, x, y))

    for n in Noeuds:
        Candidats = []
        for autre in Noeuds:
            if n != autre:
                d = distance(n, autre)
                if d <= DIST_MAX_LIAISON:
                    Candidats.append((autre, d))

        Candidats.sort(key=lambda item: item[1])

        for voisin, dist_visuelle in Candidats[:MAX_VOISINS]:
            poids = round(random.uniform(1.0, 5.0), 1)

            if not any(l.cible == voisin for l in n.liaisons):
                n.liaisons.append(Liaison(voisin, poids))
            if not any(l.cible == n for l in voisin.liaisons):
                voisin.liaisons.append(Liaison(n, poids))

    return Noeuds


def afficher_liaisons(screen, noeuds):
    Arcs_dessines = set()
    for n in noeuds:
        for l in n.liaisons:
            cle = tuple(sorted([n.id, l.cible.id]))
            if cle not in Arcs_dessines:
                pygame.draw.line(screen, (60, 60, 60), n.position(), l.cible.position(), 1)
                Arcs_dessines.add(cle)


def afficher_graphe(screen, noeuds, font):
    if AFFICHER_LIAISONS:
        afficher_liaisons(screen, noeuds)

    for n in noeuds:
        ratio = min(n.temps_non_visite / TEMPS_MAX, 1.0)
        r = int(255 * ratio)
        v = int(255 * (1 - ratio))
        col = (r, v, 0)

        pygame.draw.circle(screen, col, n.position(), RAYON_NOEUD)

        txt = font.render(str(n.id), True, (255, 255, 255))
        screen.blit(txt, (n.x + 12, n.y - 10))


def afficher_agents(screen, agents, font):
    for a in agents:
        pos = (int(a.x), int(a.y))
        pygame.draw.circle(screen, (50, 120, 255), pos, RAYON_AGENT)

        txt = font.render(f"a{a.id}", True, (255, 255, 255))
        screen.blit(txt, (a.x + 10, a.y))


def creer_agents(noeuds, nb_agents):
    Agents = []
    for i in range(nb_agents):
        start = random.choice(noeuds)
        a = Agent(i, start)
        a.vitesse = VITESSE_AGENTS
        # supr choisir_destination(a, Agents, TEMPS_SIMULATION) car inutil + chiant avec les prog qui veult des init
        Agents.append(a)
    return Agents


def copier_graphe(noeuds_source):
    Correspondance = {}

    for n in noeuds_source:
        Correspondance[n.id] = Noeud(n.id, n.x, n.y)

    for n in noeuds_source:
        for liaison in n.liaisons:
            Correspondance[n.id].liaisons.append(
                Liaison(Correspondance[liaison.cible.id], liaison.poids)
            )

    return list(Correspondance.values())


def charger_algorithme(chemin, numero):
    nom_module = f"algo_test_{numero}"

    spec = importlib.util.spec_from_file_location(nom_module, chemin)

    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    return module #return modul et pas juste la fonction


def executer_test(noeuds_base, positions_depart, algo, graine, temps_simulation, inclure_intervalles=False):
    random.seed(graine)

    Noeuds = copier_graphe(noeuds_base)

    Poids = [
        liaison.poids
        for n in Noeuds
        for liaison in n.liaisons
    ]

    poids_moyen = sum(Poids) / len(Poids) if Poids else 1.0
    vitesse = 4.0 * poids_moyen if poids_moyen > 0 else 0.1

    Par_id = {n.id: n for n in Noeuds}

    Agents = []
    for i, id_depart in enumerate(positions_depart):
        agent = Agent(i, Par_id[id_depart])
        agent.vitesse = vitesse
        Agents.append(agent)

    #supr dt_max = 1.0 / FPS car plus pas de temps fix pareil pour la suite
    temps_ecoule = 0.0

    while temps_ecoule < temps_simulation:
        #dt = min(dt_max, temps_simulation - temps_ecoule)

        #for n in Noeuds:
            #n.temps_non_visite += dt

        for agent in Agents:
            if agent.destination is None:
                algo(agent, Agents, temps_simulation)

            #agent.avancer(dt)

        #temps_ecoule += dt

        #AJOUT : on cherche le temps du prochain event (agent qui trouv dest)
        prochain_temps = temps_simulation
        for agent in Agents:
            if agent.destination is not None:
                temps_restant = agent.temps_trajet_total - agent.temps_trajet_ecoule

                # pour empécher pes dt = 0 à cause d'arondit de float
                if temps_restant <= 0:
                    agent.avancer(temps_restant) # Nettoie et met l'agent à sa destination
                else:
                    temps_arrivee = temps_ecoule + temps_restant
                    if temps_arrivee < prochain_temps:
                        prochain_temps = temps_arrivee


        dt = prochain_temps - temps_ecoule
        if dt <= 0:
            dt = 0.001

        for n in Noeuds:
            n.temps_non_visite += dt

        for agent in Agents:
            if agent.destination is not None:
                agent.avancer(dt)

        temps_ecoule = prochain_temps

        #temps_ecoule += dt

    Intervalles = []
    for n in Noeuds:
        Intervalles.extend(n.temps_visites)

    if not Intervalles:
        if inclure_intervalles:
            return None, None, []
        return None, None

    idleness_moyenne = sum(Intervalles) / len(Intervalles)
    idleness_max = max(Intervalles)

    if inclure_intervalles:
        return idleness_moyenne, idleness_max, Intervalles
    return idleness_moyenne, idleness_max


def afficher_bilan(nom, resultats):
    Moyennes = [
        r[0] for r in resultats
        if r[0] is not None
    ]
    Maximums = [
        r[1] for r in resultats
        if r[1] is not None
    ]

    print(f"\nalgo : {nom}")
    if Moyennes:
        # idlenes moy : min, max et moy
        min_moy = min(Moyennes)
        max_moy = max(Moyennes)
        avg_moy = sum(Moyennes) / len(Moyennes)
        print(f"idlenes moy -> min: {min_moy:.2f}s, max: {max_moy:.2f}s, moy: {avg_moy:.2f}s")

        # idlenes max : min, max et moy
        min_max = min(Maximums)
        max_max = max(Maximums)
        avg_max = sum(Maximums) / len(Maximums)
        print(f"idlenes max -> min: {min_max:.2f}s, max: {max_max:.2f}s, moy: {avg_max:.2f}s")
    else:
        print("ancune visite enregister.")


#AJOUT
import matplotlib.pyplot as plt
from matplotlib.lines import Line2D

def visualiser_resultats(Resultats, graph=False, mode=1):
    if not graph:
        return

    algos = list(Resultats.keys())

    if mode == 1:
        # MODE 1 : 2 abscisses (Idleness Moyenne et Maximum) avec des échelles séparées (twinx)
        fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(14, 6))
        num_algos = len(algos)
        colors = plt.cm.tab10(range(num_algos))

        for i, (nom_algo, res_list) in enumerate(Resultats.items()):
            moyennes = [r[0] for r in res_list if r[0] is not None]
            maximums = [r[1] for r in res_list if r[1] is not None]

            col = colors[i]
            for axe, valeurs, position in (
                (ax1, moyennes, i),
                (ax2, maximums, i)
            ):
                if valeurs:
                    axe.scatter(position - 0.15, min(valeurs), color=col, marker='o', s=90, zorder=3)
                    axe.scatter(position, sum(valeurs) / len(valeurs), color=col, marker='^', s=90, zorder=3)
                    axe.scatter(position + 0.15, max(valeurs), color=col, marker='s', s=90, zorder=3)

            ax1.plot([], [], color=col, marker='o', linestyle='None', markersize=8, label=nom_algo)

        for axe, titre, etiquette in (
            (ax1, "Idleness moyenne", "Idleness moyenne (secondes)"),
            (ax2, "Idleness maximale", "Idleness maximale (secondes)")
        ):
            axe.set_xticks(range(len(algos)))
            axe.set_xticklabels(algos, rotation=30, ha="right")
            axe.set_ylabel(etiquette)
            axe.set_title(titre)
            axe.grid(True, linestyle='--', alpha=0.4)

        ax1.legend(title="Algorithmes", loc='best', framealpha=0.9)
        ax2.legend(
            handles=[
                Line2D([], [], color="black", marker="o", linestyle="None", label="Minimum"),
                Line2D([], [], color="black", marker="^", linestyle="None", label="Moyenne"),
                Line2D([], [], color="black", marker="s", linestyle="None", label="Maximum")
            ],
            title="Statistiques",
            loc="best"
        )
        fig.tight_layout()
        plt.show()

    elif mode == 2:
        # MODE 2 : Courbe en pointillé pour la moyenne et zone remplie pour le max par test
        fig, ax = plt.subplots(figsize=(12, 6))

        for nom_algo, res_list in Resultats.items():
            tests = list(range(len(res_list)))
            moyennes = [r[0] if r[0] is not None else 0 for r in res_list]
            maximums = [r[1] if r[1] is not None else 0 for r in res_list]

            # Courbe moyenne en pointillé
            ligne, = ax.plot(tests, moyennes, linestyle='--', label=f"{nom_algo} (Moyenne)")
            couleur = ligne.get_color()

            # Courbe max et zone remplie
            ax.plot(tests, maximums, linestyle='-', color=couleur, alpha=0.8, label=f"{nom_algo} (Maximum)")
            ax.fill_between(tests, 0, maximums, color=couleur, alpha=0.12)

        ax.set_title("Évolution de l'Idleness (Moyenne et Maximum) sur les tests de graphes")
        ax.set_xlabel("Numéro du Graphe / Test")
        ax.set_ylabel("Idleness (secondes)")
        ax.legend(loc='upper right', bbox_to_anchor=(1.25, 1))
        plt.grid(True, linestyle='--', alpha=0.6)
        plt.tight_layout()
        plt.show()
#fin AJOUT

def init_modul(module_algo):
    # AJOUT : réinnitialisation des var glob du fichier emcapsulé
    if hasattr(module_algo, 'initialise'):
        module_algo.initialise = False
    if hasattr(module_algo, 'circuits_agents'):
        module_algo.circuits_agents.clear()
    if hasattr(module_algo, 'objectifs_agents'):
        module_algo.objectifs_agents.clear()
    if hasattr(module_algo, 'clusters_noeuds'):
        module_algo.clusters_noeuds.clear()

def comparer_algorithmes(graph, mode):
    fenetre = Tk()
    fenetre.withdraw()

    Dossier = filedialog.askdirectory(
        title="choisir dossier des .graph"
    )
    if not Dossier:
        fenetre.destroy()
        return

    Fichiers_graphes = sorted(
        glob.glob(os.path.join(Dossier, "*.graph"))
    )

    nb_aleatoires = simpledialog.askinteger(
        "graphes alea",
        "combiens de graphes alea ?",
        initialvalue=0,
        minvalue=0,
        parent=fenetre
    )
    if nb_aleatoires is None:
        fenetre.destroy()
        return

    # tu peux en selectioner autant que tu veux mtn
    Fichiers_algos = filedialog.askopenfilenames(
        title="choisire les algos python a comparer",
        filetypes=[("fichiers python", "*.py")],
        parent=fenetre
    )

    fenetre.destroy()

    if len(Fichiers_algos) < 2:
        print("fo au moins 2 fichiez .py pr comparer")
        return

    Algos = [
        (os.path.basename(path), charger_algorithme(path, i))
        for i, path in enumerate(Fichiers_algos)
    ]

    Jeux_graphes = []

    for chemin in Fichiers_graphes:
        graphe = ouvrir_graphe(chemin)
        Jeux_graphes.append((os.path.basename(chemin), graphe))

    for i in range(nb_aleatoires):
        random.seed(2000 + i)
        graphe = creer_graphe(NB_NOEUDS)
        Jeux_graphes.append((f"graphe alea {i + 1}", graphe))

    if not Jeux_graphes:
        return

    Resultats = {nom: [] for nom, _ in Algos}

    for numero, (nom_graphe, graphe) in enumerate(Jeux_graphes):
        if not graphe:
            continue

        random.seed(1000 + numero)
        Positions_depart = [
            random.choice(graphe).id
            for _ in range(NB_AGENTS)
        ]

        temps_simulation = max(30, len(graphe) / 4)

        for nom_algo, module_algo in Algos:
            init_modul(module_algo)

            moyenne, maximum = executer_test(
                graphe,
                Positions_depart,
                module_algo.choisir_destination,  # On passe bien la fonction du module
                graine=5000 + numero,
                temps_simulation=temps_simulation
            )
            Resultats[nom_algo].append((moyenne, maximum))

    print("\nbilan final")
    for nom_algo, _ in Algos:
        afficher_bilan(nom_algo, Resultats[nom_algo])
    visualiser_resultats(Resultats, graph, mode)


# =========================
# MAIN
# =========================

def lancer_algo():
    global AFFICHER_LIAISONS
    pygame.init()
    screen = pygame.display.set_mode((LARGEUR, HAUTEUR))
    pygame.display.set_caption("simulasion d'agent")
    clock = pygame.time.Clock()
    temps_simu = 0

    font_noeuds = pygame.font.SysFont(None, 20)
    font_agents = pygame.font.SysFont(None, 18)

    chemin_graphe = choisir_fichier_graphe()

    if chemin_graphe:
        try:
            Noeuds = ouvrir_graphe(chemin_graphe)
        except (ET.ParseError, OSError, ValueError):
            Noeuds = creer_graphe(NB_NOEUDS)
    else:
        Noeuds = creer_graphe(NB_NOEUDS)

    Agents = creer_agents(Noeuds, NB_AGENTS)

    for agent in Agents:
        print(
            f"Après init : agent {agent.id}, "
            f"position={agent.noeud_actuel.id}, "
            f"destination={agent.destination.id if agent.destination else None}"
        )

    running = True
    while running:
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_l:
                    AFFICHER_LIAISONS = not AFFICHER_LIAISONS

        dt = clock.get_time() / 1000.0
        temps_simu += dt

        for n in Noeuds:
            n.temps_non_visite += dt

        for a in Agents:
            if a.destination is None:
                choisir_destination(a, Agents, TEMPS_SIMULATION)
            a.avancer(dt)

        screen.fill((25, 25, 25))
        afficher_graphe(screen, Noeuds, font_noeuds)
        afficher_agents(screen, Agents, font_agents)

        pygame.display.flip()
        clock.tick(FPS)

        if temps_simu >= TEMPS_SIMULATION:
            running = False

    pygame.quit()

    Temps_attente = []
    for n in Noeuds:
        Temps_attente.extend(n.temps_visites)

    if Temps_attente:
        moy = sum(Temps_attente) / len(Temps_attente)
        max_t = max(Temps_attente)

        print(f"temps simu: {TEMPS_SIMULATION}s")
        print(f"nb visites: {len(Temps_attente)}")
        print(f"idlenes moy: {moy:.2f}s")
        print(f"idlenes max: {max_t:.2f}s")

def rapport_createur():
    nb_aleatoires = 5
    range_nb_agent = [i for i in range(3, 10, 2)]
    fenetre = Tk()
    fenetre.withdraw()

    #Choix du dossier contenant les graphes
    Dossier = filedialog.askdirectory(
        title="choisir dossier des .graph"
    )
    if not Dossier:
        fenetre.destroy()
        return

    Fichiers_graphes = sorted(
        glob.glob(os.path.join(Dossier, "*.graph"))
    )

    # tu peux en selectioner autant que tu veux mtn
    Fichiers_algos = filedialog.askopenfilenames(
        title="choisire les algos python a comparer",
        filetypes=[("fichiers python", "*.py")],
        parent=fenetre
    )

    fenetre.destroy()

    if len(Fichiers_algos) < 2:
        print("faut au moins 2 fichiez .py pour comparer")
        return

    Algos = [
        (os.path.basename(path), charger_algorithme(path, i))
        for i, path in enumerate(Fichiers_algos)
    ]

    Jeux_graphes = []

    for chemin in Fichiers_graphes:
        graphe = ouvrir_graphe(chemin)
        Jeux_graphes.append((os.path.basename(chemin), graphe))

    for i in range(nb_aleatoires):
        random.seed(2000 + i)
        graphe = creer_graphe(NB_NOEUDS)
        Jeux_graphes.append((f"graphe alea {i + 1}", graphe))

    if not Jeux_graphes:
        return

    Resultats = {
        nom: {nb_agents: [] for nb_agents in range_nb_agent}
        for nom, _ in Algos
    }
    Intervalles_par_algo = {
        nom: [] for nom, _ in Algos
    }

    for numero, (_, graphe) in enumerate(Jeux_graphes):
        if not graphe:
            continue

        random.seed(1000 + numero)
        Positions_depart = [
            random.choice(graphe).id
            for _ in range(max(range_nb_agent))
        ]

        temps_simulation = max(30, len(graphe) / 4)

        for nb_agents in range_nb_agent:
            positions_agents = Positions_depart[:nb_agents]
            for nom_algo, algo in Algos:
                init_modul(algo)
                moyenne, maximum, intervalles = executer_test(
                    graphe,
                    positions_agents,
                    algo.choisir_destination,
                    graine=5000 + numero,
                    temps_simulation=temps_simulation,
                    inclure_intervalles=True
                )
                Resultats[nom_algo][nb_agents].append((moyenne, maximum))
                Intervalles_par_algo[nom_algo].extend(intervalles)

    if not any(
        resultat[0] is not None or resultat[1] is not None
        for resultats_par_agent in Resultats.values()
        for resultats in resultats_par_agent.values()
        for resultat in resultats
    ):
        print("Aucun résultat exploitable pour générer les graphiques.")
        return

    couleurs = plt.get_cmap("turbo", len(Algos))
    marqueurs = [
        "o", "s", "^", "D", "v", "P", "X", "*", "<", ">",
        "1", "2", "3", "4", "8", "p", "h", "H", "+", "x",
        "d", "|", "_", "."
    ]

    figure = plt.figure(figsize=(10, 5), constrained_layout=True)
    grille = figure.add_gridspec(1, 2)
    axe_max = figure.add_subplot(grille[0, 0])
    axe_moyenne = figure.add_subplot(grille[0, 1])
    mesures_graphes = [
        (axe_max, 1, "Idleness maximale moyenne (s)", "Idleness maximale moyenne"),
        (axe_moyenne, 0, "Idleness moyenne (s)", "Idleness moyenne")
    ]

    for axe, indice, etiquette_y, titre in mesures_graphes:
        for index, (nom_algo, _) in enumerate(Algos):
            valeurs_x = []
            valeurs_y = []
            for nb_agents in range_nb_agent:
                mesures = []
                for resultat in Resultats[nom_algo][nb_agents]:
                    valeur = resultat[indice]
                    if valeur is not None:
                        mesures.append(valeur)

                if mesures:
                    valeurs_x.append(nb_agents)
                    valeurs_y.append(sum(mesures) / len(mesures))

            axe.plot(
                valeurs_x,
                valeurs_y,
                label=nom_algo,
                color=couleurs(index),
                marker=marqueurs[index % len(marqueurs)],
                linestyle="-"
            )

        axe.set_title(titre)
        axe.set_ylabel(etiquette_y)
        axe.set_xticks(range_nb_agent)
        axe.grid(True, linestyle="--", alpha=0.5)
        axe.legend()
    plt.show()

if __name__ == "__main__":
    #comparer_algorithmes(graph=True, mode=2)
    lancer_algo()
    #rapport_createur()
