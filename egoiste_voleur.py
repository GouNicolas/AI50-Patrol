from collections import deque
import math
import heapq
import itertools

# circuit de patrouille par id d'agent
circ_ag = {}
obj_ag = {}
cl_nd = {}
dist_gl = {}
chem_gl = {}
init_ok = False


def initialisation(ag_lst):
    global circ_ag, obj_ag
    global cl_nd, dist_gl, chem_gl, init_ok

    circ_ag = {}
    obj_ag = {}
    cl_nd = {}
    dist_gl = {}
    chem_gl = {}
    init_ok = False

    if not ag_lst:
        return

    # recup de tou les nds accessibles depuis les agts
    tous_nd = set()
    file_att = deque(
        a.noeud_actuel for a in ag_lst
        if a.noeud_actuel is not None
    )

    while file_att:
        nd = file_att.popleft()
        if nd in tous_nd:
            continue
        tous_nd.add(nd)
        for l in nd.liaisons:
            if l.cible not in tous_nd:
                file_att.append(l.cible)

    nd_lst = list(tous_nd)
    if not nd_lst:
        print("[debug erreur]aucun noeud truv !")
        return

    nb_ag = len(ag_lst)
    if nb_ag > len(nd_lst):
        print("attension : plu d'agent ke de noeud")

    ag_tries = sorted(ag_lst, key=lambda a: a.id)

    # Dijkstra globale stricte
    def calc_tt_dist(nd_cib):
        d_dict = {}
        c_dict = {}
        cpt = itertools.count()
        for orig in nd_cib:
            d = {orig: 0.0}
            prec = {}
            f_d = [(0.0, next(cpt), orig)]
            while f_d:
                cout, _, n = heapq.heappop(f_d)
                if cout > d[n]:
                    continue
                for l in n.liaisons:
                    voi = l.cible
                    nv_cout = cout + l.poids
                    if nv_cout < d.get(voi, float("inf")):
                        d[voi] = nv_cout
                        prec[voi] = n
                        heapq.heappush(f_d, (nv_cout, next(cpt), voi))
            d_dict[orig] = d
            c_dict[orig] = {}
            for arr in nd_cib:
                if arr in d:
                    chem = [arr]
                    cour = arr
                    while cour != orig:
                        if cour not in prec:
                            break
                        cour = prec[cour]
                        chem.append(cour)
                    chem.reverse()
                    c_dict[orig][arr] = chem
        return d_dict, c_dict

    dist_gl, chem_gl = calc_tt_dist(nd_lst)

    # selection des graines les plus eloignees
    prem_dep = next(
        (a.noeud_actuel for a in ag_tries if a.noeud_actuel in nd_lst),
        nd_lst[0]
    )
    graines = [prem_dep]

    while len(graines) < nb_ag:
        cand = [n for n in nd_lst if n not in graines]
        if not cand:
            break
        suiv = max(
            cand,
            key=lambda n: min(
                dist_gl.get(n, {}).get(g, float("inf"))
                for g in graines
            )
        )
        if dist_gl.get(suiv, {}).get(graines[0], float("inf")) == float("inf"):
            rest_acc = [c for c in cand if dist_gl.get(c, {}).get(graines[0], float("inf")) != float("inf")]
            if rest_acc:
                suiv = rest_acc[0]
        graines.append(suiv)

    # init cluster
    clusters = {ag_tries[i].id: [graines[i % len(graines)]] for i in range(nb_ag)}
    nd_non_ass = set(nd_lst)
    for g in graines:
        if g in nd_non_ass:
            nd_non_ass.remove(g)

    for aid, cl in clusters.items():
        ref = cl[0]
        if nd_non_ass:
            proch = min(
                nd_non_ass,
                key=lambda n: dist_gl.get(ref, {}).get(n, float("inf"))
            )
            cl.append(proch)
            nd_non_ass.remove(proch)

    # parcours Dijkstra
    def const_parc_mes(dep, grp):
        grp_lst = list(grp)
        if len(grp_lst) <= 1:
            return [grp_lst[0]], 0.0

        non_vis = set(grp_lst)
        if dep in non_vis:
            non_vis.remove(dep)
        tour = [dep]
        cour = dep

        while non_vis:
            suiv = min(
                non_vis,
                key=lambda n: dist_gl.get(cour, {}).get(n, float("inf"))
            )
            tour.append(suiv)
            non_vis.remove(suiv)
            cour = suiv

        amel = True
        it_2 = 0
        while amel and it_2 < 20:
            it_2 += 1
            amel = False
            n_taille = len(tour)
            for i in range(1, n_taille - 1):
                for j in range(i + 1, n_taille):
                    a = tour[i - 1]
                    b = tour[i]
                    c = tour[j]
                    d = tour[(j + 1) % n_taille]
                    if b in dist_gl.get(a, {}) and d in dist_gl.get(c, {}) and \
                       c in dist_gl.get(a, {}) and b in dist_gl.get(d, {}):
                        anc = dist_gl[a][b] + dist_gl[c][d]
                        nouv = dist_gl[a][c] + dist_gl[b][d]
                        if nouv < anc:
                            tour[i:j + 1] = reversed(tour[i:j + 1])
                            amel = True

        parc = [tour[0]]
        t_tot = 0.0
        for i in range(len(tour)):
            orig = tour[i]
            arr = tour[(i + 1) % len(tour)]
            if arr in chem_gl.get(orig, {}):
                chem = chem_gl[orig][arr]
                for k in range(len(chem) - 1):
                    u_k = chem[k]
                    v_k = chem[k+1]
                    liai = next((l for l in u_k.liaisons if l.cible == v_k), None)
                    if liai:
                        t_tot += liai.poids
                parc.extend(chem[1:])
            else:
                parc.append(arr)

        return parc, t_tot

    circ_temp = {}
    tps_clust = {}

    def recal_tt_circ():
        nonlocal circ_temp, tps_clust
        circ_temp = {}
        tps_clust = {}
        for aid, cl in clusters.items():
            if not cl:
                continue
            ag_ref = next((a for a in ag_lst if a.id == aid), None)
            dep = ag_ref.noeud_actuel if ag_ref and ag_ref.noeud_actuel in cl else cl[0]
            p, t = const_parc_mes(dep, cl)
            circ_temp[aid] = p
            tps_clust[aid] = t

    recal_tt_circ()

    #glouton
    while nd_non_ass:
        id_crt = min(tps_clust, key=tps_clust.get)
        tps_anc = tps_clust[id_crt]

        m_nd = None
        m_ins = None
        m_del = float("inf")

        for n_lib in nd_non_ass:
            cl_tst = clusters[id_crt] + [n_lib]
            _, tps_nouv = const_parc_mes(cl_tst[0], cl_tst)
            delta = tps_nouv - tps_anc
            if delta < m_del:
                m_del = delta
                m_nd = n_lib
                m_ins = cl_tst

        if m_nd is not None:
            clusters[id_crt] = m_ins
            nd_non_ass.remove(m_nd)
        else:
            n_sec = list(nd_non_ass)[0]
            clusters[id_crt].append(n_sec)
            nd_non_ass.remove(n_sec)

        recal_tt_circ()

    stabil = False
    it_max = 25
    it = 0

    #vol, don, échange
    while not stabil and it < it_max:
        it += 1
        stabil = True
        max_l_act = max(tps_clust.values())
        id_lrd = max(tps_clust, key=tps_clust.get)
        id_crt = min(tps_clust, key=tps_clust.get)

        if id_crt == id_lrd or len(clusters[id_lrd]) <= 2:
            continue

        cand_vol = sorted(
            clusters[id_lrd],
            key=lambda n: dist_gl.get(clusters[id_crt][0], {}).get(n, float("inf"))
        )

        mvt_eff = False
        for n_tst in cand_vol:
            if len(clusters[id_lrd]) <= 2:
                break
            clusters[id_lrd].remove(n_tst)
            clusters[id_crt].append(n_tst)

            recal_tt_circ()
            nv_max = max(tps_clust.values())

            if nv_max < max_l_act:
                stabil = False
                mvt_eff = True
                break
            else:
                clusters[id_crt].remove(n_tst)
                clusters[id_lrd].append(n_tst)
                recal_tt_circ()

        if mvt_eff:
            continue

        ech_eff = False
        for aid, cl_cib in clusters.items():
            if aid == id_lrd:
                continue
            for n_lrd in list(clusters[id_lrd]):
                if len(clusters[id_lrd]) <= 2:
                    break
                for n_cib in list(cl_cib):
                    clusters[id_lrd].remove(n_lrd)
                    cl_cib.remove(n_cib)
                    clusters[id_lrd].append(n_cib)
                    cl_cib.append(n_lrd)

                    recal_tt_circ()
                    nv_max = max(tps_clust.values())

                    if nv_max < max_l_act:
                        stabil = False
                        ech_eff = True
                        break
                    else:
                        clusters[id_lrd].remove(n_cib)
                        cl_cib.remove(n_lrd)
                        clusters[id_lrd].append(n_lrd)
                        cl_cib.append(n_cib)
                        recal_tt_circ()
                if ech_eff:
                    break
            if ech_eff:
                break

    prop = {}
    for aid, cl in clusters.items():
        for n in cl:
            prop[n] = aid

    for agent in ag_tries:
        grp = clusters.get(agent.id, set())
        if not grp:
            continue

        circ = circ_temp.get(agent.id, [agent.noeud_actuel])
        if not circ:
            circ = list(grp)

        circ_ag[agent.id] = circ
        obj_ag[agent.id] = 1 if len(circ) > 1 else 0

        if agent.noeud_actuel not in circ:
            agent.noeud_actuel = circ[0]
            agent.x = circ[0].x
            agent.y = circ[0].y

        agent.destination = None
        agent.noeud_depart_trajet = agent.noeud_actuel
        agent.temps_trajet_total = 0.0
        agent.temps_trajet_ecoule = 0.0

    cl_nd = prop.copy()
    init_ok = True


def choisir_destination(agent, ag_lst, TEMPS_SIMULATION):
    global init_ok, cl_nd, circ_ag, dist_gl

    if not init_ok:
        initialisation(ag_lst)

    if agent.destination is not None:
        return

    nd_act = agent.noeud_actuel
    if nd_act is None:
        return

    circ = circ_ag.get(agent.id, [])
    if len(circ) < 2:
        return

    idx = obj_ag.get(agent.id, 1)
    if idx >= len(circ):
        idx = 1

    if nd_act == circ[idx]:
        idx = (idx + 1) % len(circ)
        if idx == 0:
            idx = 1
    elif circ[idx - 1] != nd_act:
        pos = [
            i for i, nd in enumerate(circ)
            if nd == nd_act and i > 0
        ]
        if pos:
            idx = (pos[0] + 1) % len(circ)
            if idx == 0:
                idx = 1

    cib_init = circ[idx]
    cib = cib_init

    liai_dir = next((l for l in nd_act.liaisons if l.cible == cib_init), None)
    cout_dir = liai_dir.poids if liai_dir else math.dist((nd_act.x, nd_act.y), (cib_init.x, cib_init.y))

    for l in nd_act.liaisons:
        voi = l.cible
        prop_voi = cl_nd.get(voi)

        if prop_voi is not None and prop_voi != agent.id and voi not in circ[:3]:
            liai_vers_voi = l
            liai_voi_cib = next((lv for lv in voi.liaisons if lv.cible == cib_init), None)
            cout_voi_cib = liai_voi_cib.poids if liai_voi_cib else math.dist((voi.x, voi.y), (cib_init.x, cib_init.y))

            cout_det = liai_vers_voi.poids + cout_voi_cib
            surc_ag = cout_det - cout_dir

            if surc_ag > 0:
                circ_aut = circ_ag.get(prop_voi, [])
                if voi in circ_aut:
                    idx_voi = circ_aut.index(voi)
                    av = circ_aut[idx_voi - 1]
                    ap = circ_aut[(idx_voi + 1) % len(circ_aut)]

                    d_act_aut = dist_gl.get(av, {}).get(voi, 0) + dist_gl.get(voi, {}).get(ap, 0)
                    d_sans_voi = dist_gl.get(av, {}).get(ap, 0)

                    econ_aut = d_act_aut - d_sans_voi

                    if econ_aut > surc_ag:
                        cib = voi
                        break

    liai_trv = next(
        (l for l in nd_act.liaisons if l.cible == cib),
        None
    )

    if liai_trv is None:
        meill_liai = min(
            nd_act.liaisons,
            key=lambda l: l.poids,
            default=None
        )
        if meill_liai:
            liai_trv = meill_liai
            cib = meill_liai.cible
        else:
            return

    obj_ag[agent.id] = idx
    agent.destination = cib
    agent.noeud_depart_trajet = nd_act
    agent.temps_trajet_total = (
        liai_trv.poids / agent.vitesse
        if agent.vitesse > 0
        else float("inf")
    )
    agent.temps_trajet_ecoule = 0.0
