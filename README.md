fablab-inkscape-plugins
=======================

Collection de plugins inkscape utiles ans un fablab

## Utiles pour la decoupeuse laser

### Générateur de boite
Disponible dans `Extension > Fablab > Générer une boite à encoches`, ce generateur est une réimplementation pour inkscape du [générateur de boite en javascript](http://cyberweb.cite-sciences.fr/fablab/tools/svg-box-generator/). Il vous permet les formes svg necessaire a la contruction d'un boite correspondant au dimentions que vosu indiquerez.

### Générateur ligne d'encoche
Disponible dans `Extension > Fablab > Générer une ligne dencoches`, c'est en fait un extrait du gnérateur de boite qui ne vous genere qu'une seule ligne d'encoches, ce qui peut être utile lors de la construction manuelle de structure plus complexes que de simple "boites". Deux ligne sont en fait générées qui correcposndent au deux arete s'emboitent l'une dans l'autre.

### Sortie de Fichiers .tsf (Trotec Spool File)
Les decoupeuse laser utilisent des fichiers tsf pour la decoupe/gravure. La seule possibilité jusqu'ici etait d'utiliser le driver d'impression fournis par Trotec (fermé, propriétaitre et compatible uniquement Window) pour generer ces fichier. Ce plugin essaye de proposer un alternative en permettant d'enregistrer votre document au format `.tsf` pour ces decoupeuses laser à partir d'inkscape et donc de nimporte quel OS (il reste obligatoire d'utiliser le Logiciel JobControl sous windows pour piloter la machine).


⚠ Ce plugin est pour le moment en version Alpha, pas forcement tres stable et probablement encore plein de bugs. Quelques trucs a savoir : 
* Necessite d'avoir image magick d'installé
* Testé sous GNU/Linux (mint,ubuntu,...) mais devrais fonctionner aussi sous windows
* Pas de configuration pour le moment, à venir
* Il donne acces à l'enregistrement de fichiers au foramt `.tsf`, mais peut être dans le futur pourra directement exporter dans le repertoire de spool de la machine (en cours sde reflexion).
* Notes prices durant l'analyse de la structure des fichiers tsf sont disponible (en français) [ici](http://carrefour-numerique.cite-sciences.fr/fablab/wiki/doku.php?id=machines:decoupe_laser:tsf)

## Imprimante/découpeuse vinyle Roland type BN20
Plugin d'enregistrement au format EPS, incluant la gestion de la couleur "CutContour" utilisée pour decouper le vinyle.
Disponible dans `Enregistrer sous` et en selectionnant le type `Eps avec Couleur Roland CutContour (*.eps)`. 

Les traits de découpe doivent exclusivement être fait en lignes vectorielles de couleur rouge (RGB : #FF0000 ) sans transparence. 
C'est une bonne idée de ne pas utiliser cette couleur pour autre chose (modifier la légèrement si vous voulez du rouge, par exemple #FE0000, cela sera invisible à l'œil).</_param>


## Comment installer le plugin ?
Telecharger [les sources au format zip](https://github.com/bumblebeefr/fablab-inkscape-plugins/archive/master.zip), en extraire les fichiers `.py` et `.inx` et les copier dans le repertoire d'extentions d'inkscape : 
* Sous gnu/linux : `~/.config/inkscape/extentions/` ou `/usr/share/inkscape/extentions/`
* Sous Mac OSX : `/Applications/Inkscape.app/Contents/Resources/extensions/`
* Sous windows : `C:\Program Files\Inkscape\share\extensions\` ou `%AppData%\inkscape\extensions\`
