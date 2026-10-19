Tu vas écrire les points clés d'une réunion, à partir de sa transcription automatique. Le lecteur a une minute : il veut savoir ce qui s'est dit d'important, ce qui change et ce qu'il doit retenir pour la suite.

Format de la transcription : une ligne par prise de parole, sous la forme « Nom du locuteur : texte ». « Unknown speaker 1 », « Unknown speaker 2 », etc. désignent des locuteurs non identifiés. La transcription vient d'une reconnaissance vocale : noms propres mal orthographiés, phrases coupées entre deux lignes, parfois des phrases parasites.

<<<DÉBUT DE LA TRANSCRIPTION>>>
{}
<<<FIN DE LA TRANSCRIPTION>>>

# RÈGLES
- Un point clé est un fait, un résultat, une décision, un chiffre ou un enseignement que le lecteur doit connaître. Il tient en une phrase et contient au moins un élément précis : un nom, un chiffre, une date, un produit, une décision.
- Choisis les points par importance, pas par ordre chronologique. Couvre toute la réunion, la fin comprise.
- Cas particulier : si toute la transcription n'a qu'un seul nom de locuteur (par exemple « speaker » ou « Unknown speaker 1 »), la reconnaissance des locuteurs n'a pas fonctionné et plusieurs personnes parlent sous ce nom. Les participants sont alors les personnes qui se présentent ou que l'on interpelle par leur nom et qui répondent, suivies de « (déduit) » ; n'écris pas le nom de locuteur unique. Un porteur qu'on ne peut pas identifier s'écrit « Participant non identifié ».
- Mets en gras avec **…** le mot ou le chiffre qui porte le point.
- « Ce qui change » : uniquement ce qui a été décidé ou appris pendant la réunion et qui modifie la situation d'avant.
- « À retenir pour la suite » : prochaines étapes, échéances et engagements dits pendant la réunion, avec le porteur quand il est dit. N'invente jamais une échéance.
- Conserve les chiffres avec leur unité et ce à quoi ils se rapportent.
- Ignore les salutations, apartés, plaisanteries et le bruit de reconnaissance vocale (« Sous-titres par… », une ligne isolée qui n'est qu'une liste de noms de produits).
- Rédige dans la langue majoritaire de la réunion, titres compris. Aucune phrase vide comme « la réunion a été productive ».

# FORMAT DE SORTIE

Markdown brut, jamais entouré d'un bloc de code, sans phrase d'introduction. La réponse commence par la ligne « ## L'essentiel ». Sections, dans cet ordre, avec exactement ces titres :

1. « ## L'essentiel » : une seule phrase de 30 mots maximum.
2. « ## Points clés » : 5 à 8 puces, les plus importantes d'abord, 25 mots maximum chacune.
3. « ## Ce qui change » : 1 à 4 puces. « Rien de nouveau. » si rien.
4. « ## À retenir pour la suite » : 1 à 4 puces.
5. « ## Chiffres clés » : une puce par chiffre ou date utile, au format « - **valeur** : ce à quoi elle se rapporte ». « Aucun. » si rien.
6. « ## Thèmes » : une puce par thème abordé (2 à 5 mots), suivie de 1 à 3 sous-puces de 8 mots maximum avec les faits de ce thème.
7. « ## Participants » : une puce par participant. Avec plusieurs noms de locuteurs : la liste exacte de ces noms, sans en ajouter. Avec un seul nom de locuteur : les personnes déduites selon la règle ci-dessus, suivies de « (déduit) ».

# RAPPEL
1. La réponse commence par « ## L'essentiel », sans bloc de code.
2. Chaque point clé contient un élément précis et un passage en gras.
3. Rien d'inventé : ni décision, ni échéance, ni chiffre.
4. Participants : les noms de locuteurs, sauf transcription à locuteur unique (personnes déduites, « (déduit) »).
