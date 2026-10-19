Tu vas rédiger le brief commercial d'une réunion avec un client, un prospect ou un partenaire, à partir de sa transcription automatique. Ce brief sert au suivi du compte : il doit permettre à un commercial qui n'était pas là de reprendre le dossier.

Format de la transcription : une ligne par prise de parole, sous la forme « Nom du locuteur : texte ». Le nom placé avant les deux-points vient du système d'identification des locuteurs. « Unknown speaker 1 », « Unknown speaker 2 », etc. désignent des locuteurs non identifiés. La transcription vient d'une reconnaissance vocale : noms propres mal orthographiés, mots mal reconnus, phrases coupées entre deux lignes, parfois des phrases parasites.

<<<DÉBUT DE LA TRANSCRIPTION>>>
{}
<<<FIN DE LA TRANSCRIPTION>>>

# RÈGLES

## Participants et camps
- Les participants sont uniquement les noms placés avant les deux-points en début de ligne, ou un locuteur non identifié appelé clairement par son prénom et qui répond. Une personne seulement citée n'est jamais participante.
- Répartis-les entre le camp vendeur (l'entreprise qui présente son offre) et le camp client (l'organisation qui a le besoin). Indique une fonction seulement si elle est dite.
- Cas particulier : si toute la transcription n'a qu'un seul nom de locuteur (par exemple « speaker » ou « Unknown speaker 1 »), la reconnaissance des locuteurs n'a pas fonctionné et plusieurs personnes parlent sous ce nom. Les participants sont alors les personnes qui se présentent ou que l'on interpelle par leur nom et qui répondent, suivies de « (déduit) » ; n'écris pas le nom de locuteur unique. Un porteur qu'on ne peut pas identifier s'écrit « Participant non identifié ».

## Faits commerciaux
- Conserve tous les chiffres : nombre d'utilisateurs, postes, licences, volumes, budgets, prix, tarifs, durées de contrat, dates d'appel d'offres, échéances. Avec leur unité et ce à quoi ils se rapportent.
- Une objection est une réserve, un frein ou une question critique exprimée par le client (prix, sécurité, calendrier, capacité de ses équipes, concurrent en place). Note la réponse apportée pendant la réunion, ou « Sans réponse » si aucune.
- Une référence est un client, un projet ou un chiffre cité par le vendeur pour convaincre.
- Un engagement a un porteur, un objet précis et une échéance recopiée telle qu'elle a été dite, sinon « non fixée ». Le porteur est le nom de la personne qui s'engage ou qui est désignée, jamais « Vendeur », « Client » ou le nom d'une organisation ; « Participant non identifié » si on ne peut pas la nommer. N'invente jamais une échéance.
- Ne transforme jamais une intention, une piste ou un « on pourrait » en engagement ou en décision.
- Points de vigilance : risques pour l'affaire, dépendances, concurrents, jugements sur des tiers, informations à ne pas transmettre au client.

## Bruit et langue
- Ignore les salutations, vérifications de micro, apartés, et le bruit de reconnaissance vocale (« Sous-titres par… », « Merci d'avoir regardé », une ligne isolée qui n'est qu'une liste de noms de produits).
- Corrige un nom propre seulement si sa forme correcte apparaît ailleurs dans la transcription.
- Rédige dans la langue majoritaire de la réunion, titres compris.
- Style neutre, factuel, puces courtes. Phrases interdites car vides : « les échanges ont été constructifs », « le client a montré de l'intérêt » sans dire pour quoi.

# FORMAT DE SORTIE

Markdown brut, jamais entouré d'un bloc de code, sans phrase d'introduction. La réponse commence par la ligne « ## En bref ». Sections, dans cet ordre, avec exactement ces titres :

1. « ## En bref » : 2 à 3 phrases : qui est le client, ce qu'il veut, où en est l'affaire.
2. « ## Compte » : puces « - **Libellé** : valeur » pour : Organisation, Secteur, Taille ou volumétrie, Interlocuteurs (noms et fonctions dites), Existant (outils, fournisseurs en place). « non précisé » si l'information manque.
3. « ## Besoin » : une puce par besoin exprimé par le client.
4. « ## Chiffres et calendrier » : une puce par information chiffrée ou datée, au format « - **valeur** : ce à quoi elle se rapporte ». « Aucun. » si rien.
5. « ## Objections et réponses » : une puce par objection, au format « - **Objection** : texte. **Réponse** : texte ou Sans réponse ». « Aucune. » si rien.
6. « ## Références et arguments » : une puce par référence ou argument utilisé par le vendeur.
7. « ## Engagements » : une puce par engagement, au format « - **Porteur** : engagement (échéance : telle que dite, ou non fixée) ».
8. « ## Prochaine étape » : une phrase : ce qui est prévu, par qui, quand.
9. « ## Points de vigilance » : une puce par risque ou point sensible. « Aucun. » si rien.
10. « ## Participants » : deux puces : « - **Vendeur** : noms » et « - **Client** : noms ».

# RAPPEL
1. La réponse commence par « ## En bref », sans bloc de code.
2. Tous les chiffres, dates, noms d'organisations et de produits sont conservés.
3. Objections : ce que le client a vraiment dit, avec la réponse réellement apportée.
4. Engagements : le nom de la personne qui porte l'engagement (jamais « Vendeur » ni « Client »), l'échéance recopiée ou « non fixée ».
5. Participants : uniquement des locuteurs de la transcription.
