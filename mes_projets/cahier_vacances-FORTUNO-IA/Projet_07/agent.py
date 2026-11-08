# L'agent de voyage, écrit automatiquement depuis le notebook du Projet 07.
from datetime import datetime, timedelta

from utils import encoder, requete


def outil_vols(conn, destination, date_depart, voyageurs=1):
    """
    Outil : trouve les vols disponibles vers une destination, un jour donné.

    Arguments :
    conn -- une connexion ouverte vers voyages.db
    destination -- le nom de la ville, tel qu'écrit dans la table
    date_depart -- le jour du départ, au format "2026-08-12"
    voyageurs -- le nombre de places nécessaires

    Retourne :
    vols -- un DataFrame des vols trouvés, du moins cher au plus cher
    """

    ### START CODE HERE ###

    sql ="""

           SELECT numero,origine,heure_depart,duree_h,prix_eur,places_restantes
           FROM vols 
           WHERE destination= ? AND date_depart= ? AND places_restantes>= ?
           ORDER BY prix_eur


      """  

    ### END CODE HERE ###

    return requete(conn, sql, (destination, date_depart, voyageurs))


def outil_activites(conn, ville):
    """
    Outil : liste les activités proposées dans une ville, de la moins chère à la plus chère.

    Arguments :
    conn -- une connexion ouverte vers voyages.db
    ville -- le nom de la ville

    Retourne :
    activites -- un DataFrame des activités de la ville
    """

    ### START CODE HERE ###

    # (1) les colonnes, (2) le filtre sur la ville, (3) le tri de la moins chère à la plus chère
    sql = """
          SELECT nom,categorie,duree_h,prix_eur
          FROM activites
          WHERE ville= ?
          ORDER BY prix_eur


         """

    ### END CODE HERE ###

    return requete(conn, sql, (ville,))


def outil_hotels(brochures, encodeur, ville, envie, k=3):
    """
    Outil : trouve les hôtels d'une ville qui correspondent le mieux à une envie écrite librement.

    Arguments :
    brochures -- le DataFrame retourné par charger_brochures
    encodeur -- le modèle retourné par charger_encodeur
    ville -- le nom de la ville
    envie -- ce que cherche le voyageur, avec ses mots à lui
    k -- le nombre d'hôtels à retourner

    Retourne :
    hotels -- un DataFrame des k meilleures brochures, avec une colonne "score", les meilleures d'abord
    """
    hotels_ville = brochures[brochures["ville"] == ville].reset_index(drop=True)

    ### START CODE HERE ###

    vecteurs = encoder(encodeur,hotels_ville["resume"])               # (1) une ligne par brochure de la ville
    vecteur_envie = encoder(encodeur,[envie])[0]      # (2) un seul vecteur pour la demande
    hotels_ville["score"] = vecteurs @ vecteur_envie    # (3) vecteurs normalisés : produit scalaire = cosinus
    hotels = hotels_ville.sort_values("score",ascending=False).head(k).reset_index(drop=True)     # (4)

    ### END CODE HERE ###

    return hotels


def chiffrer_voyage(vol, hotel, activites, nuits):
    """
    Calcule le prix total d'un voyage, par personne.

    Arguments :
    vol -- une ligne du DataFrame des vols
    hotel -- une ligne du DataFrame des hôtels
    activites -- une liste de dictionnaires, chacun avec une clé "prix_eur"
    nuits -- le nombre de nuits

    Retourne :
    total -- le prix total en euros, par personne
    """
    prix_vol = vol["prix_eur"]
    prix_hotel = hotel["prix_nuit"] * nuits
    prix_activites = sum(a["prix_eur"] for a in activites)
    return float(prix_vol + prix_hotel + prix_activites)


def dates_voisines(date_depart, ecart=2):
    """
    Les jours à explorer autour de la date demandée, du plus proche au plus lointain.

    Arguments :
    date_depart -- le jour souhaité, au format "2026-08-12"
    ecart -- de combien de jours on accepte de s'éloigner

    Retourne :
    voisines -- la liste des autres dates, sans la date demandée elle-même
    """
    jour = datetime.strptime(date_depart, "%Y-%m-%d")
    voisines = []
    for decalage in range(1, ecart + 1):
        for signe in (-1, 1):
            voisines.append((jour + timedelta(days=signe * decalage)).strftime("%Y-%m-%d"))
    return voisines


def essayer_une_date(demande, conn, brochures, encodeur):
    """
    Compose le meilleur voyage possible pour UN jour de départ donné.

    Arguments :
    demande -- un dictionnaire avec destination, date_depart, nuits, voyageurs, budget_max, envie
    conn, brochures, encodeur -- les sources de données de l'agent

    Retourne :
    voyage -- un dictionnaire décrivant le voyage, ou None si rien ne rentre dans le budget
    journal -- la liste des ajustements faits par l'agent, une phrase par sacrifice
    """
    vols = outil_vols(conn, demande["destination"], demande["date_depart"], demande["voyageurs"])
    hotels = outil_hotels(brochures, encodeur, demande["destination"], demande["envie"])
    activites = outil_activites(conn, demande["destination"])

    journal = []
    if vols.empty or hotels.empty:
        return None, ["aucun vol ou aucun hôtel disponible pour cette destination et cette date"]

    vol = vols.iloc[0]                              # le vol le moins cher
    retenues = activites.to_dict("records")         # toutes les activités, pour commencer
    impossible = False

    # L'ordre dans lequel on essaiera les hôtels : le plus pertinent d'abord, puis ceux qui
    # coûtent vraiment moins cher que lui, du plus cher au moins cher, pour descendre en douceur.
    prix_du_premier = hotels.iloc[0]["prix_nuit"]
    replis = [j for j in range(1, len(hotels)) if hotels.iloc[j]["prix_nuit"] < prix_du_premier]
    ordre = [0] + sorted(replis, key=lambda j: hotels.iloc[j]["prix_nuit"], reverse=True)
    position = 0                                    # où on en est dans la liste ordre

    for _ in range(30): # garde-fou anti-boucle infinie
        hotel = hotels.iloc[ordre[position]]
        total = chiffrer_voyage(vol, hotel, retenues, demande["nuits"])

        # Une ligne par combinaison essayée, pour voir l'agent chercher.
        ecart = total - demande["budget_max"]
        verdict = "OK" if ecart <= 0 else f"dépasse de {ecart:.0f}"
        print(f"   {demande['date_depart'][8:]}/{demande['date_depart'][5:7]}  {hotel['hotel'][:20]:20s} "
              f"vol {vol['prix_eur']:4.0f} + hôtel {hotel['prix_nuit'] * demande['nuits']:5.0f} "
              f"+ sorties {sum(a['prix_eur'] for a in retenues):4.0f} = {total:6.0f} EUR   {verdict}")

        if total <= demande["budget_max"]:
            break                                   # le plan tient dans le budget : on s'arrête là

        payantes = [a for a in retenues if a["prix_eur"] > 0]

        if payantes: # repli n°1 : sacrifier une sortie
            ### START CODE HERE ###
            plus_chere = max(payantes,key=lambda a:a["prix_eur"]) # (1) la sortie la plus chère
            retenues = [a for a in retenues if a is not plus_chere]   # (2) on la retire du programme
            position = 0 # (3) on repart du meilleur hôtel
            ### END CODE HERE ###
            journal.append(f"j'ai retiré « {plus_chere['nom']} » ({plus_chere['prix_eur']:.0f} EUR)")

        elif position + 1 < len(ordre):             # repli n°2 : descendre d'un hôtel
            ### START CODE HERE ###
            position = position + 1 # (4) l'hôtel suivant de la liste
            ### END CODE HERE ###
            journal.append(f"{hotel['hotel']} restait trop cher, "
                           f"j'ai pris {hotels.iloc[ordre[position]]['hotel']} à la place")

        else: # plus rien à relâcher
            ### START CODE HERE ###
            impossible = True# (5) l'agent renonce
            ### END CODE HERE ###
            journal.append("je n'avais plus rien à sacrifier ce jour-là")

        if impossible:
            return None, journal

    voyage = {"destination": demande["destination"], "date_depart": demande["date_depart"],
              "nuits": demande["nuits"], "voyageurs": demande["voyageurs"],
              "vol": vol, "hotel": hotels.iloc[ordre[position]], "activites": retenues,
              "prix_total": total, "budget_max": demande["budget_max"]}
    return voyage, journal


def planifier(demande, conn, brochures, encodeur):
    """
    L'agent complet : il compose le voyage demandé, puis explore les jours voisins.

    Arguments :
    demande -- un dictionnaire avec destination, date_depart, nuits, voyageurs, budget_max, envie
    conn, brochures, encodeur -- les sources de données de l'agent

    Retourne :
    voyage -- le voyage pour la date demandée, ou None si rien n'y rentre
    journal -- les ajustements de l'agent, et le bon plan qu'il a repéré ailleurs
    """
    print(f"[agent] {demande['destination']}, {demande['nuits']} nuits, "
          f"{demande['voyageurs']} voyageur(s), budget {demande['budget_max']:.0f} EUR par personne")

    voyage, journal = essayer_une_date(demande, conn, brochures, encodeur)

    # On rejoue exactement le même raisonnement pour chaque jour voisin. Seul le prix du
    # vol change d'un jour à l'autre : les hôtels et les activités, eux, ne bougent pas.
    alternatives = []
    for autre_jour in dates_voisines(demande["date_depart"]):
        candidat, _ = essayer_une_date(dict(demande, date_depart=autre_jour), conn, brochures, encodeur)
        if candidat is not None:
            alternatives.append(candidat)

    if not alternatives:
        return voyage, journal

    if voyage is None:
        # Rien ne rentrait le jour demandé : on signale le jour voisin le moins cher.
        secours = min(alternatives, key=lambda v: v["prix_total"])
        jour = datetime.strptime(secours["date_depart"], "%Y-%m-%d").strftime("%d/%m")
        journal.append(f"en revanche, en partant le {jour}, un voyage à "
                       f"{secours['prix_total']:.0f} EUR par personne devenait possible")
        return voyage, journal

    ### START CODE HERE ###

    meilleure = max(alternatives,key=lambda v: (len(v["activites"]), -v["prix_total"])) # (1) le meilleur jour voisin
    sorties_en_plus = len(meilleure["activites"]) - len(voyage["activites"])   # (2) les sorties gagnées
    economie = voyage["prix_total"] - meilleure["prix_total"]     # (3) les euros gagnés

    ### END CODE HERE ###

    jour = datetime.strptime(meilleure["date_depart"], "%Y-%m-%d").strftime("%d/%m")
    if sorties_en_plus > 0:
        journal.append(f"au passage, en partant le {jour} vous gardiez "
                       f"{len(meilleure['activites'])} sorties au lieu de {len(voyage['activites'])}, "
                       f"pour {meilleure['prix_total']:.0f} EUR")
    elif economie >= 10:
        journal.append(f"au passage, en partant le {jour} le même programme revenait à "
                       f"{meilleure['prix_total']:.0f} EUR, soit {economie:.0f} EUR de moins par personne")

    return voyage, journal


def reserver(conn, voyage, client, confirme=False):
    """
    Enregistre le voyage dans la table reservations, mais seulement si le voyageur a confirmé.

    Arguments :
    conn -- une connexion ouverte vers voyages.db
    voyage -- le dictionnaire retourné par planifier
    client -- le nom du voyageur
    confirme -- doit valoir True pour que quoi que ce soit soit écrit

    Retourne :
    message -- ce qui s'est passé, en clair
    """
    if voyage is None:
        return "Rien à réserver : aucun voyage n'a été trouvé."

    # LE GARDE-FOU. Trois lignes, et c'est la partie la plus importante du fichier :
    # tant que le voyageur n'a pas dit oui, la fonction ressort sans rien avoir écrit.
    if not confirme:
        return (f"Rien n'a été réservé. Le voyage à {voyage['destination']} coûterait "
                f"{voyage['prix_total']:.0f} EUR par personne, soit "
                f"{voyage['prix_total'] * voyage['voyageurs']:.0f} EUR au total. "
                f"Il faut confirmer pour que la réservation soit enregistrée.")

    ### START CODE HERE ###

    sql = """
          INSERT INTO reservations
          (client,destination,date_depart,nuits,voyageurs,vol,hotel,activites,prix_total,reservee_le)
          VALUES(?,?,?,?,?,?,?,?,?,?)

          """  # (1) dix colonnes, donc dix points d'interrogation

    ### END CODE HERE ###

    conn.execute(sql, (client, voyage["destination"], voyage["date_depart"], voyage["nuits"],
                       voyage["voyageurs"], voyage["vol"]["numero"], voyage["hotel"]["hotel"],
                       ", ".join(a["nom"] for a in voyage["activites"]),
                       voyage["prix_total"] * voyage["voyageurs"],
                       datetime.now().strftime("%Y-%m-%d %H:%M")))

    ### START CODE HERE ###

    # (2) enregistre le résultat dans la base de données

    ### END CODE HERE ###

    return (f"C'est réservé pour {client} : {voyage['destination']}, "
            f"{voyage['nuits']} nuits, {voyage['prix_total'] * voyage['voyageurs']:.0f} EUR au total.")
