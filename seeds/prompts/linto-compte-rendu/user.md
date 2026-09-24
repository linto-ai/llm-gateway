Tu vas rédiger le compte rendu d'une réunion professionnelle tenue en visioconférence, à partir de sa transcription automatique.

Format de la transcription : une ligne par prise de parole, sous la forme « Nom du locuteur : texte ». Le nom placé avant les deux-points vient du système d'identification des locuteurs. « Unknown speaker 1 », « Unknown speaker 2 », etc. désignent des locuteurs non identifiés. La transcription vient d'une reconnaissance vocale : elle contient des noms propres mal orthographiés, des mots mal reconnus, des phrases coupées entre deux lignes et parfois des phrases parasites.

<<<DÉBUT DE LA TRANSCRIPTION>>>
{}
<<<FIN DE LA TRANSCRIPTION>>>

# TA MISSION

Produire un compte rendu fidèle, factuel et directement utilisable par une personne qui n'a pas assisté à la réunion. Chaque phrase apporte un fait : qui, quoi, combien, quand. Tu n'inventes rien : ce qui n'est pas dans la transcription n'existe pas.

# RÈGLES

## Participants
- Les participants sont uniquement les noms placés avant les deux-points en début de ligne. Personne d'autre.
- Une personne seulement nommée dans les propos (collègue absent, client, personne citée) n'est jamais un participant. Elle va dans la section « Personnes mentionnées ».
- Un « Unknown speaker N » garde ce nom, sauf si un participant l'appelle clairement par son prénom et qu'il répond. Écris alors « Prénom (Unknown speaker N) ».
- N'attribue jamais une fonction ou un rôle qui n'est pas dit explicitement dans la transcription. Dans le doute, écris le nom seul.
- Recopie les noms des locuteurs exactement comme ils apparaissent, y compris une adresse e-mail.
- Cas particulier : si toute la transcription n'a qu'un seul nom de locuteur (par exemple « speaker » ou « Unknown speaker 1 »), la reconnaissance des locuteurs n'a pas fonctionné et plusieurs personnes parlent sous ce nom. Les participants sont alors les personnes qui se présentent ou que l'on interpelle par leur nom et qui répondent, suivies de « (déduit) » ; n'écris pas le nom de locuteur unique. Un porteur qu'on ne peut pas identifier s'écrit « Participant non identifié ».

## Décisions
- Une décision est un choix explicitement acté pendant la réunion, par exemple : « on part sur », « c'est validé », « on fait comme ça », « ok, on le fait ».
- Une proposition, une idée, une intention, une hypothèse, un souhait, un constat ou un accord « sous réserve » n'est pas une décision. Place-le dans « Pistes et propositions non actées ».
- Un refus n'est jamais transformé en décision inverse.
- S'il n'y a aucune décision, écris seulement « Aucune décision actée. ». Ne remplis jamais une section pour la remplir.

## Actions
- Une action a un porteur, un objet précis et une échéance.
- Le porteur est la personne qui s'engage (« je vais », « je m'en occupe », « je t'envoie ») ou celle qui est désignée nommément. Si personne n'est désigné, écris « Porteur à définir ». Ne déplace jamais une action vers une autre personne que celle qui s'est engagée.
- L'échéance est recopiée exactement comme elle a été dite : « demain », « lundi après-midi », « la semaine prochaine », « avant le comité ». Si aucune échéance n'est dite, écris « non fixée ». N'invente jamais une date ni un délai.
- Ce qui a déjà été fait pendant la réunion n'est pas une action à mener.

## Chiffres, dates et noms
- Conserve tous les chiffres utiles : montants, prix, budgets, volumes, nombres d'utilisateurs, pourcentages, durées, dates, versions, avec leur unité et ce à quoi ils se rapportent.
- Conserve les noms d'organisations, de clients, de produits, de projets et d'outils.
- Ne remplace jamais une information précise par une formule vague comme « un budget limité », « plusieurs clients » ou « prochainement ».

## Erreurs de reconnaissance vocale
- Ignore les phrases parasites sans lien avec la conversation : génériques de sous-titres (« Sous-titres par… », « Sous-titrage Société Radio-Canada », « Merci d'avoir regardé »), ou une ligne isolée qui n'est qu'une énumération de noms de produits sans phrase autour.
- Corrige un nom propre mal reconnu seulement si sa forme correcte apparaît ailleurs dans la transcription. Sinon, recopie-le tel quel.
- Les plaisanteries, apartés et digressions ne sont pas des sujets de la réunion.

## Couverture et longueur
- Couvre toute la réunion, du début à la fin. La fin contient souvent les décisions, les engagements et la suite : lis-la avec la même attention que le début.
- La longueur suit la richesse de la réunion. Une réunion dense d'une heure produit un compte rendu long et détaillé.
- Préfère des puces courtes et factuelles aux paragraphes. Une puce contient un fait.

## Langue et style
- Rédige dans la langue majoritaire de la transcription, titres de sections compris. Si la réunion se tient en anglais, tout le compte rendu est en anglais.
- Style neutre, à la troisième personne, sans dialogue, sans hésitations orales, sans longue citation.
- Phrases interdites car vides : « les participants ont souligné l'importance de… », « des ajustements sont nécessaires », « la réunion a permis de faire le point », « des échanges ont eu lieu ».

# FORMAT DE SORTIE

Markdown brut. La réponse commence directement par la ligne « ## En bref » et se termine par la dernière section. Aucun texte avant ou après, aucun bloc de code, aucune balise HTML, aucun émoji, aucun crochet. Pas de ligne Date, Durée ou Rédacteur.

Écris les sections suivantes, dans cet ordre, avec exactement ces titres :

1. « ## En bref » : 2 à 4 phrases. L'objet de la réunion, ses principaux résultats, la suite prévue.
2. « ## Participants » : une puce par participant. Le nom, suivi de sa fonction seulement si elle est dite.
3. « ## Personnes mentionnées » : une puce par personne citée mais absente, avec en quelques mots pourquoi elle est citée. « Aucune. » si personne.
4. « ## Sujets abordés » : liste numérotée des sujets, dans l'ordre de la réunion.
5. « ## Décisions actées » : une puce par décision, avec la personne qui l'a prise si c'est dit.
6. « ## Pistes et propositions non actées » : une puce par proposition, avec qui la porte. « Aucune. » si rien.
7. « ## Actions à mener » : une puce par action, au format : - **Porteur** : action précise (échéance : telle que dite, ou non fixée)
8. « ## Chiffres et dates clés » : une puce par information chiffrée ou datée, au format : - **valeur** : ce à quoi elle se rapporte. « Aucun. » si rien.
9. « ## Discussion » : un sous-titre « ### » par sujet, dans l'ordre des sujets abordés. Sous chaque sous-titre, 3 à 8 puces factuelles : positions exprimées avec leur auteur, arguments, contraintes, chiffres.
10. « ## Points ouverts » : questions non tranchées, informations manquantes, risques signalés. « Aucun. » si rien.
11. « ## Prochaine réunion » : date, horaire et objet s'ils sont dits, sinon « Non fixée. »
12. Uniquement si la réunion aborde des sujets RH nominatifs (salaire, recrutement, départ, évaluation, santé) : « ## Confidentialité » avec une phrase qui signale ces sujets sans les détailler.

# RAPPEL : CE QUI COMPTE LE PLUS

1. Participants : uniquement les noms en début de ligne. Les personnes citées vont dans « Personnes mentionnées ».
2. Décisions : uniquement ce qui est explicitement acté, sinon « Aucune décision actée. ».
3. Actions : le vrai porteur, l'échéance recopiée ou « non fixée ». Rien d'inventé.
4. Tous les chiffres, montants, dates et noms propres utiles sont conservés.
5. Langue de la transcription. La réponse commence par « ## En bref », sans texte avant, sans bloc de code.
