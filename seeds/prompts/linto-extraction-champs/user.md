Tu remplis les champs d'un modèle de document Word à partir d'un compte rendu de réunion déjà rédigé.

<<<DÉBUT DU COMPTE RENDU>>>
{{output}}
<<<FIN DU COMPTE RENDU>>>

Champs à remplir, sous forme de liste JSON. Chaque champ s'écrit « nom: consigne ». La consigne dit quoi extraire et sous quelle forme :
{{metadata_fields}}

Règles :
1. Réponds uniquement avec un objet JSON valide. Aucun texte avant ou après, aucun bloc de code.
2. Les clés sont les noms des champs, c'est-à-dire la partie avant le premier « : ».
3. Chaque valeur est une chaîne de caractères, sauf quand la consigne demande une « list of JSON objects » (liste d'objets JSON) : la valeur est alors un tableau d'objets, avec exactement les clés indiquées, chaque valeur d'objet étant une chaîne. Un nombre s'écrit entre guillemets, par exemple "3".
4. Quand une consigne de type chaîne demande plusieurs éléments, mets-les dans la même chaîne, un élément par ligne, lignes séparées par \n, avec le préfixe demandé (par exemple « • »). Tu peux mettre en gras un nom de personne ou un chiffre clé avec **…**.
5. Prends l'information dans le compte rendu. N'ajoute rien qui n'y figure pas. Si l'information est absente, utilise la valeur par défaut donnée par la consigne, sinon null. La valeur par défaut (« Aucun », « non précisé »…) remplace toute la valeur quand rien n'est trouvé : ne l'ajoute jamais après des éléments trouvés.
6. Respecte les limites de longueur et de nombre d'éléments données par la consigne. Pour choisir les éléments les plus importants, privilégie ceux qui ont un porteur, une échéance, un montant ou une conséquence pour la suite.
7. Recopie les noms de personnes, les chiffres et les échéances exactement comme dans le compte rendu.
8. Écris dans la langue du compte rendu. En dehors du gras **…**, aucun markdown dans les valeurs : ni #, ni lien, ni tableau.
9. Une liste d'objets suit l'ordre du compte rendu et respecte le nombre maximal d'éléments de la consigne. Tableau vide [] si rien ne correspond.

Exemple de réponse pour trois champs fictifs, dont une liste d'objets :
{"titre": "Migration de la messagerie du service achats", "nb_actions": "2", "actions": [{"porteur": "Julie", "action": "Envoyer le devis", "echeance": "vendredi"}, {"porteur": "Marc", "action": "Réserver la salle", "echeance": "non fixée"}]}
