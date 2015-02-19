fablab-inkscape-plugins
=======================

Collection de plugins inkscape utiles ans un fablab

Ces plugins sont fonctionels avec les versions `0.48.x` et `0.91` d'inkscape.

## Utiles pour la découpeuse laser

### Générateur de boites
Disponible dans `Extension > Fablab > Générer une boite à encoches`, ce générateur est une ré-implémentation pour inkscape de mon [générateur de boite en javascript](http://cyberweb.cite-sciences.fr/fablab/tools/svg-box-generator/). Il vous permet de dessiner automatiquement les formes svg nécessaires à la construction d'une boite correspondant aux dimensions que vous indiquerez.

### Générateur ligne d'encoche
Disponible dans `Extension > Fablab > Générer une ligne d'encoches`, c'est en fait un extrait du générateur de boites qui ne vous génère qu'une seule ligne d'encoches, ce qui peut être utile lors de la construction manuelle de structures plus complexes que de simple "boites". Deux ligne sont en fait générées qui correspondent aux deux arêtes qui s’emboîtent l'une dans l'autre.

### Sortie de Fichiers .tsf (Trotec Spool File)
Les découpeuses laser TROTEC utilisent des fichiers `.tsf` pour la découpe/gravure. La seule possibilité jusqu'ici était d'utiliser le driver d'impression fournis par TROTEC (fermé, propriétaire et compatible uniquement avec Window) pour générer ces fichiers. Ce plugin essaye de proposer un alternative permettant d'enregistrer/exporter votre document au format `.tsf` pour ces découpeuses laser à partir d'inkscape et donc de n'importe quel OS (il reste obligatoire d'utiliser le Logiciel JobControl sous Windows pour piloter la machine).

⚠ Ce plugin est pour le moment en version Beta, utilisable probablement non dépourvu de bugs.

Quelques trucs à savoir :
* Nécessite d'avoir image magick d'installé
* Testé sous GNU/Linux (mint,ubuntu,...) et un peu sous windows7/XP mais devrait fonctionner aussi sous freebsd et macosx
* Il donne accès à l'enregistrement de fichiers au format `.tsf`
* Aussi accessible via le menu `Extension > Fablab > Exporter en fichier Trotec Spool File (TSF)`
  * Il faut, dans ce cas, ne pas oublier de configurer le répertoire de spool (répertoire où seront exportées les fichier tsf)
  * Il est possible de cette façons d'exporter uniquement la sélection en cochant la case appropriée
* Les notes prises durant l'analyse de la structure des fichiers tsf sont disponible (en français) [ici](http://carrefour-numerique.cite-sciences.fr/fablab/wiki/doku.php?id=machines:decoupe_laser:tsf)
* La générations des images noir&blanc utilisées pour la gravure n'ont pas été peaufinées. À venir !
* L'installation de Xvfb sur GNU/Linux (`sudo apt-get install xvfb` sous debian et dérivés) permet d'éviter l'affichage d'une fenêtre d'inkscape supplémentaire durant l'export et d'abaisser légèrement le temps d'export)

## Imprimante/découpeuse vinyle Roland type BN20
Plugin d'enregistrement au format EPS, incluant la gestion de la couleur "CutContour" utilisée pour découper le vinyle.
Disponible dans `Enregistrer sous` et en sélectionnant le type `Eps avec Couleur Roland CutContour (*.eps)`.

Les traits de découpe doivent exclusivement être fait en lignes vectorielles (contours) de couleur rouge (RGB : #FF0000 ) sans transparence.
C'est une bonne idée de ne pas utiliser cette couleur pour autre chose (modifier la légèrement si vous voulez du rouge, par exemple #FE0000, cela sera invisible à l'œil).


## Comment installer les plugins ?
Télécharger [les sources au format zip](https://github.com/bumblebeefr/fablab-inkscape-plugins/archive/master.zip), en extraire les fichiers commençant par  `fablab_` et les copier dans le répertoire d’extensions d'inkscape :
* Sous gnu/linux, FreeBSD : `~/.config/inkscape/extentions/` ou `/usr/share/inkscape/extentions/`
* Sous mac OSX : `/Applications/Inkscape.app/Contents/Resources/extensions/`
* Sous windows : `C:\Program Files\Inkscape\share\extensions\` ou `%AppData%\inkscape\extensions\`

Installer imagemagick (utilisé par le plugin d'export au format TSF pour découpeuses laser) :
* Sous gnu/linux, FreeBSD : Installer imagemagick avec votre gestionnaire de packets préféré, ou [télécharger le binaire prépackagé](http://www.imagemagick.org/script/binary-releases.php#unix)
* Sous mac OSX : Utiliser [macport](http://www.imagemagick.org/script/binary-releases.php#macosx) ou bien plus simplement [télécharger l'installeur prépackagé par cactuslab](http://cactuslab.com/imagemagick/assets/ImageMagick-6.9.0-0.pkg.zip)
* Sous windows : [Télécharger l'installeur correspondant à votre version de windows](http://www.imagemagick.org/script/binary-releases.php#windows)
