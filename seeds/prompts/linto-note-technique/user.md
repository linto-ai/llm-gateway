Tu vas rédiger la note technique d'une réunion technique (revue d'architecture, cadrage, post-mortem, revue de code, choix d'outil), à partir de sa transcription automatique. Cette note sert à un ingénieur qui n'était pas là : il doit comprendre le problème, les options, ce qui est tranché et ce qu'il reste à faire.

Format de la transcription : une ligne par prise de parole, sous la forme « Nom du locuteur : texte ». Le nom placé avant les deux-points vient du système d'identification des locuteurs. « Unknown speaker 1 », « Unknown speaker 2 », etc. désignent des locuteurs non identifiés. La transcription vient d'une reconnaissance vocale : noms propres et termes techniques mal orthographiés, phrases coupées entre deux lignes, parfois des phrases parasites.

<<<DÉBUT DE LA TRANSCRIPTION>>>
{}
<<<FIN DE LA TRANSCRIPTION>>>

# RÈGLES

## Faits techniques
- Conserve tous les éléments précis : noms de composants, d'outils, de versions, de commandes, de fichiers, volumes, tailles, latences, coûts, nombres de nœuds ou de GPU, dates. Avec leur unité.
- Un terme technique mal reconnu est corrigé seulement si sa forme correcte apparaît ailleurs dans la transcription ou si c'est un nom d'outil évident du contexte (Kubernetes, PostgreSQL, Nginx…). Sinon recopie-le tel quel.
- Une option est une solution envisagée pendant la réunion. Pour chacune : ce qu'elle apporte, ses limites, et son statut réel : Retenue (explicitement choisie), Écartée (explicitement rejetée), À étudier (ni l'un ni l'autre).
- Une décision est un choix explicitement acté. Une proposition, une intention ou un accord « sous réserve » n'est pas une décision.
- Une action a un porteur (celui qui s'engage ou qui est désigné), un objet précis et une échéance recopiée telle qu'elle a été dite, sinon « non fixée ». N'invente jamais une échéance.
- Un risque est un problème possible évoqué pendant la réunion, avec son impact et la parade discutée si elle existe.

## Participants, bruit et langue
- Les participants sont uniquement les noms placés avant les deux-points en début de ligne, ou un locuteur non identifié appelé clairement par son prénom et qui répond.
- Cas particulier : si toute la transcription n'a qu'un seul nom de locuteur (par exemple « speaker » ou « Unknown speaker 1 »), la reconnaissance des locuteurs n'a pas fonctionné et plusieurs personnes parlent sous ce nom. Les participants sont alors les personnes qui se présentent ou que l'on interpelle par leur nom et qui répondent, suivies de « (déduit) » ; n'écris pas le nom de locuteur unique. Un porteur qu'on ne peut pas identifier s'écrit « Participant non identifié ».
- Ignore les salutations, vérifications de micro, apartés, plaisanteries et le bruit de reconnaissance vocale (« Sous-titres par… », une ligne isolée qui n'est qu'une liste de noms de produits).
- Rédige dans la langue majoritaire de la réunion, titres compris. Style neutre, factuel, puces courtes. Aucune phrase vide comme « des solutions ont été discutées ».

# FORMAT DE SORTIE

Markdown brut, jamais entouré d'un bloc de code, sans phrase d'introduction. La réponse commence par la ligne « ## En bref ». Sections, dans cet ordre, avec exactement ces titres :

1. « ## En bref » : 2 à 3 phrases : le problème traité, ce qui est tranché, la suite.
2. « ## Contexte et problème » : 2 à 5 puces factuelles.
3. « ## Constats » : une puce par fait établi ou mesuré pendant la réunion, chiffres compris.
4. « ## Options étudiées » : une puce par option, au format « - **Option** : description. **Apports** : … **Limites** : … **Statut** : Retenue, Écartée ou À étudier ». « Aucune. » si rien.
5. « ## Décisions actées » : une puce par décision, avec qui l'a prise si c'est dit. « Aucune décision actée. » si rien.
6. « ## Plan d'action » : une puce par action, au format « - **Porteur** : action précise (échéance : telle que dite, ou non fixée) ».
7. « ## Risques » : une puce par risque, au format « - **Risque** : texte. **Impact** : … **Parade** : … ou non discutée ». « Aucun. » si rien.
8. « ## Questions ouvertes » : une puce par question non tranchée ou information manquante.
9. « ## Composants et références » : une puce par outil, composant, dépôt, ticket ou document cité, avec son rôle en quelques mots.
10. « ## Participants » : une puce par participant.

# RAPPEL
1. La réponse commence par « ## En bref », sans bloc de code.
2. Tous les noms techniques, versions, chiffres et unités sont conservés.
3. Statut d'une option : Retenue ou Écartée seulement si c'est explicitement dit, sinon À étudier.
4. Actions : le vrai porteur, l'échéance recopiée ou « non fixée ».
5. Participants : uniquement des locuteurs de la transcription.
