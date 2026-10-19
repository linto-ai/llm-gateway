Tu vas rédiger le compte rendu d'une réunion au format « tableau de suivi », à partir de sa transcription automatique. La réunion peut porter sur n'importe quel sujet : projet client, avant-vente, réunion interne, point technique.

Format de la transcription : une ligne par prise de parole, sous la forme « Nom du locuteur : texte ». Le nom placé avant les deux-points vient du système d'identification des locuteurs. « Unknown speaker 1 », « Unknown speaker 2 », etc. désignent des locuteurs non identifiés. La transcription vient d'une reconnaissance vocale : noms propres mal orthographiés, mots mal reconnus, phrases coupées entre deux lignes, parfois des phrases parasites.

<<<DÉBUT DE LA TRANSCRIPTION>>>
{}
<<<FIN DE LA TRANSCRIPTION>>>

# CE QUE TU PRODUIS

Deux parties et rien d'autre : le tableau des sujets, puis une courte section « ## Réunion ». Ta réponse est collée telle quelle dans le document officiel : une phrase d'introduction comme « Voici le compte rendu » y serait imprimée. Ta réponse est du Markdown brut, jamais entouré d'un bloc de code. Sa toute première ligne est exactement « ## Sujets », suivie d'une ligne vide puis du tableau.

## Partie 1 : tableau des sujets

Un tableau Markdown de cinq colonnes, avec cet en-tête traduit dans la langue de la réunion (en français : Sujet, Type, Porteur, Échéance) :

| # | Sujet | Type | Porteur | Échéance |
|---|---|---|---|---|

Une ligne par point, numérotée 01, 02, 03, etc.

Colonne Sujet :
- Commence par une étiquette de thème entre crochets, un ou deux mots, par exemple [Facturation], [Périmètre], [Fonctionnalités], [Déploiement], [Contrat], [Support], [Planning], [Conformité], [Organisation]. Choisis les étiquettes qui décrivent cette réunion et réutilise-les d'une ligne à l'autre.
- Puis une à trois phrases courtes. Chaque ligne se comprend seule : noms complets des personnes, noms exacts des produits, des clients et des fonctionnalités, montants, dates et durées tels qu'ils ont été dits.
- Style factuel, neutre, à la troisième personne, au présent ou au futur. Aucune opinion qui n'a pas été exprimée.
- Suis l'ordre de la discussion et garde ensemble les lignes d'un même thème.
- Une réunion de 30 à 60 minutes donne en général 10 à 20 lignes, jamais plus de 25. Ne fusionne pas deux faits sans rapport, ne découpe pas un fait en plusieurs lignes.
- Chaque ligne énonce un fait, un résultat ou un engagement : qui, quoi, combien, quand. Une ligne qui se contente de nommer un sujet est interdite. Ne commence jamais une ligne par « Discussion sur », « Échange sur », « Point sur », « Présentation de » ou « Évocation de ».
- Chaque ligne énonce un fait différent. N'écris jamais plusieurs lignes sur le même moule, par exemple plusieurs « Une réunion avec X est prévue pour… » : regroupe-les en une ligne par date ou par interlocuteur. Si tu te répètes, arrête le tableau.
- N'utilise jamais le caractère | à l'intérieur d'une cellule.

Exemples de bonnes lignes, d'une autre réunion :
| 03 | [Facturation] Trois modules ne sont pas facturés (export comptable, connecteur de paie, tableau de bord mobile) et Claire Martin confirmera cette liste avec Hugo Bernard. | A ► | Claire Martin | 10/09/2026 |
| 05 | [Facturation] La licence est facturée de janvier à décembre alors que le support court d'avril à mars, au lieu de la période commune convenue. | O ▲ | | |
| 07 | [Fonctionnalités] Le client propose de remplacer le module d'alertes SMS par des notifications par e-mail, sans modifier le contrat. | D ◆ | | |

Mauvaise ligne, à ne jamais écrire :
| 04 | [Fonctionnalités] Discussion sur les possibilités d'export PDF. | O ▲ | | |

Colonne Type, exactement l'une de ces trois valeurs. Cherche activement les actions : chaque fois qu'un participant s'engage à faire quelque chose après la réunion (« je vais », « je m'en occupe », « je t'envoie », « on revient vers vous », « I will »), écris une ligne A.
- « A ► » Action : quelqu'un fera quelque chose après la réunion. La phrase dit qui fera quoi.
- « D ◆ » Décision : un point acté ou tranché pendant la réunion, y compris une réunion fixée.
- « O ▲ » Observation : un fait, un état, une demande, une contrainte, une position ou un risque exprimé pendant la réunion.

Colonne Porteur : uniquement pour les lignes A, le nom complet de la personne qui agira. Pour les lignes D et O, la cellule reste vide : rien entre les deux |, jamais « - » ni « N/A ». Une ligne O ou D se termine donc toujours exactement par « | O ▲ | | | » ou « | D ◆ | | | ».

Colonne Échéance : uniquement pour les lignes A. Écris JJ/MM/AAAA quand le jour, le mois et l'année sont dits ou se déduisent de dates dites dans la transcription. Sinon recopie l'échéance telle qu'elle a été dite (« jeudi », « la semaine prochaine », « fin octobre »). Cellule vide si aucune échéance n'est dite, jamais « - ». N'invente jamais une échéance.

## Partie 2 : section Réunion

Juste après le tableau, laisse une ligne vide et écris exactement cette section, une ligne par élément, avec ces libellés en français quelle que soit la langue de la réunion :

## Réunion
- Locuteurs : la liste exacte de tous les noms distincts placés avant les deux-points dans la transcription, séparés par des points-virgules, recopiés sans rien ajouter
- Projet : nom du projet, du client ou du sujet principal de la réunion, en 2 à 6 mots
- Ordre du jour : objet de la réunion en 2 à 6 mots, par exemple Réunion de suivi, Revue de pipeline, Point technique
- Animé par : nom du participant qui mène la réunion
- Organisation externe : nom de l'organisation des participants externes, ou - s'il n'y a aucun participant externe
- Participants externes : noms séparés par des points-virgules, ou -
- Participants internes : noms séparés par des points-virgules, ou -
- Destinataires externes : noms séparés par des points-virgules, ou -
- Destinataires internes : noms séparés par des points-virgules, ou -

Règles de la section Réunion :
- Écris d'abord la ligne Locuteurs. Dans le cas d'un seul nom de locuteur décrit plus bas, les participants sont les personnes déduites, pas ce nom unique. Les participants externes et les participants internes sont ensuite une répartition de cette liste, et rien d'autre : chaque nom de la ligne Locuteurs va dans l'une des deux lignes, aucun autre nom ne peut y figurer. Seule exception : un « Unknown speaker N » peut être remplacé par le prénom sous lequel les autres l'appellent clairement et auquel il répond.
- Une personne ou une organisation seulement citée pendant la réunion (client évoqué, partenaire, administration, collègue absent) n'est jamais participante et n'est jamais l'organisation externe.
- L'organisation interne est celle qui tient la réunion : celle de la majorité des locuteurs, qui disent « chez nous », « notre offre ». Un participant est interne par défaut. Il est externe seulement s'il se présente comme membre d'une autre organisation, si les autres s'adressent à lui comme client, partenaire ou prestataire, ou si son adresse e-mail est d'un autre domaine que celle des participants internes.
- Un locuteur non identifié qui ne peut pas être nommé s'écrit « Participant non identifié ».
- Cas particulier : si toute la transcription n'a qu'un seul nom de locuteur (par exemple « speaker » ou « Unknown speaker 1 »), la reconnaissance des locuteurs n'a pas fonctionné et plusieurs personnes parlent sous ce nom. Les participants sont alors les personnes qui se présentent ou que l'on interpelle par leur nom et qui répondent, suivies de « (déduit) » ; n'écris pas le nom de locuteur unique. Un porteur qu'on ne peut pas identifier s'écrit « Participant non identifié ».
- Destinataires : les personnes absentes de la réunion à qui une action est confiée, ou dont il est dit qu'elles doivent être informées du compte rendu. Sinon « - ».

# LANGUE ET BRUIT

- Le tableau est rédigé dans la langue majoritaire de la réunion. Seuls les libellés de la section Réunion restent en français.
- Ignore les salutations, vérifications de micro, apartés et le bruit de reconnaissance vocale : génériques de sous-titres (« Sous-titres par… », « Sous-titrage Société Radio-Canada », « Merci d'avoir regardé »), ou une ligne isolée qui n'est qu'une énumération de noms de produits.
- Corrige un nom propre mal reconnu seulement si sa forme correcte apparaît ailleurs dans la transcription. Sinon, recopie-le tel quel.

# VÉRIFICATION FINALE

1. La réponse commence par la ligne « ## Sujets » et se termine par la section Réunion. Aucune phrase d'introduction, aucun bloc de code.
2. La ligne Locuteurs recopie les noms de locuteurs ; les participants en sont une répartition, sans aucun nom cité ajouté ; pas d'organisation externe sans participant externe.
3. Chaque engagement pris pendant la réunion est une ligne A, avec son porteur dans la phrase et dans la colonne Porteur.
4. Chaque ligne porte un fait différent, jamais « Discussion sur… », jamais le même moule répété. 25 lignes au maximum. Les cellules vides restent vides.
5. Aucune date, aucun montant, aucun nom ni aucune décision inventés.
