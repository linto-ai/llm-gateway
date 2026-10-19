# Template renderers

Généré par `app.services.template_renderers.render_docs()`. Un renderer est un plugin (`app/services/template_renderers/<nom>.py`) qui s'active par un élément du template et impose, le cas échéant, un contrat au prompt du service et aux consignes des placeholders.

## Renderers de sortie (agissent sur `{{output}}`)

### hidden_sections

Hidden sections: sections of the service output read by the extraction but not printed.

- **Déclencheur dans le template** : Propriété personnalisée du template hide_sections, par exemple « Réunion ».
- **Prompt du service** : Le prompt du service fait écrire une section « ## Réunion » (même nom que dans hide_sections) qui porte les données du cartouche : une ligne « - Libellé : valeur » par donnée.
- **Consignes des placeholders** : Les consignes pointent vers cette section : « valeur de la ligne Projet de la section Réunion ».
- **Exemple** : `hide_sections = Réunion ; {{projet: valeur de la ligne Projet de la section Réunion}}`
- **Étapes** : prepare_output

### output_tables

Output tables: style, widths, alignment and symbol colours of the tables of {{output}}.

- **Déclencheur dans le template** : Propriétés personnalisées du template style_table, table_widths, table_align, table_symbol_colors.
- **Prompt du service** : Le prompt du service impose un tableau Markdown avec exactement le nombre de colonnes de table_widths, l'en-tête voulu, des cellules vides plutôt que « - », et les symboles exacts de table_symbol_colors (par exemple « A ► »). Ouvrir la réponse par un titre, jamais par le tableau nu : sinon Mistral entoure le tableau d'un bloc de code.
- **Consignes des placeholders** : Aucune exigence : le tableau vient de {{output}}, pas de l'extraction.
- **Exemple** : `style_table = CRSujets ; table_widths = 5,55,7,20,13 ; table_align = center,left,center,center,center`
- **Étapes** : format_output

## Renderers de placeholders (agissent sur les valeurs extraites)

### repeated_rows

Repeated rows: a table row repeated once per object of an extracted list.

- **Déclencheur dans le template** : Placeholders pointés {{liste.champ}} dans une ligne de tableau du template.
- **Prompt du service** : Aucune exigence propre : la sortie du service doit seulement contenir l'information (par exemple une section Actions à mener).
- **Consignes des placeholders** : {{liste: consigne}} dit quoi mettre dans la liste, combien d'éléments au maximum et dans quel ordre ; {{liste.champ: consigne}} dit ce que contient chaque clé. Le gateway en fait une seule demande « list of JSON objects » au prompt d'extraction, qui doit savoir renvoyer une liste d'objets.
- **Exemple** : `| {{actions.porteur}} | {{actions: toutes les actions, 8 au maximum}}{{actions.action: 16 mots maximum}} | {{actions.echeance}} |`
- **Étapes** : before_substitution, extraction_requests

### mindmap

Mindmap: a {{mindmap_...}} placeholder becomes a mind map image drawn from an extracted outline.

- **Déclencheur dans le template** : Placeholder dont le nom commence par mindmap_, seul dans son paragraphe ou sa cellule, par exemple {{mindmap_sujets: consigne}}.
- **Prompt du service** : Aucune exigence propre : la sortie du service doit contenir les thèmes et les points à cartographier (sections Sujets abordés et Discussion par exemple).
- **Consignes des placeholders** : La consigne dit quoi cartographier (thème central, branches, détails). Le gateway la transforme en demande de plan indenté : ligne 1 le thème central, puis « - branche », puis « - détail » indenté de deux espaces.
- **Exemple** : `{{mindmap_sujets: thème central = objet de la réunion ; une branche par sujet de la section Sujets abordés ; détails = faits clés de la section Discussion}}`
- **Étapes** : before_substitution, extraction_requests

### rich_values

Rich values: a standalone multi-line or **bold** value rendered as formatted paragraphs.

- **Déclencheur dans le template** : Un placeholder seul dans son paragraphe ou sa cellule, dont la valeur a plusieurs lignes ou du **gras** ; et tout **gras** laissé dans un paragraphe après substitution (lignes répétées comprises).
- **Prompt du service** : Aucune exigence propre.
- **Consignes des placeholders** : Demander explicitement la forme : « un élément par ligne commençant par • suivi d'un espace », « nom du porteur en gras ». Le prompt d'extraction autorise **…** et le saut de ligne \n dans les valeurs.
- **Exemple** : `{{decisions_cles: les 4 décisions principales, une par ligne commençant par • suivi d'un espace, qui a tranché en gras}}`
- **Étapes** : after_substitution

## Ajouter un renderer

Créer `app/services/template_renderers/<nom>.py` avec une classe dérivée de `Renderer`, décorée par `@register`, qui définit `name`, `family`, `spec` et les seules étapes de sa famille. Régénérer ce fichier.

