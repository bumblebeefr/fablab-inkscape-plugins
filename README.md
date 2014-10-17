fablab-inkscape-plugins
=======================

Collection de plugins inkscape utiles ans un fablab

## Utiles pour la decoupeuse laser

### Générateur de boite
Disponible dans `Extension > Fablab > Générer une boite à encoches`, ce generateur est une réimplementation pour inkscape du [générateur de boite en javascript](http://cyberweb.cite-sciences.fr/fablab/tools/svg-box-generator/). Il vous permet les formes svg necessaire a la contruction d'un boite correspondant au dimentions que vosu indiquerez.

### Générateur ligne d'encoche
Disponible dans `Extension > Fablab > Générer une ligne dencoches`, c'est en fait un extrait du gnérateur de boite qui ne vous genere qu'une seule ligne d'encoches, ce qui peut être utile lors de la construction manuelle de structure plus complexes que de simple "boites". Deux ligne sont en fait générées qui correcposndent au deux arete s'emboitent l'une dans l'autre.

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
