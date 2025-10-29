# sha-666
SHA-666 — Premier algorithme de hashage quantique (PoC)
Présentation du projet

SHA-666 est un projet expérimental visant à démontrer le premier prototype de hashage quantique fonctionnant sur les ordinateurs quantiques d’IBM Q Experience.
Il s’agit d’un Proof of Concept (PoC) qui explore comment le calcul quantique peut être utilisé pour créer un algorithme de hashage inviolable sans décryptage classique possible — autrement dit, un hash dont l’inversion n’est réalisable qu’à l’aide d’un ordinateur quantique.

Le nom SHA-666 est une référence symbolique :

"SHA" pour Secure Hash Algorithm, et "666" pour marquer la transition vers la 6ᵉ génération d’algorithmes de sécurité, celle de l’ère quantique.

Objectif du PoC

Le but de ce PoC est de :

Convertir le SHA-256 classique en version quantique, exécutée sur un quantum circuit IBM Qiskit.

Démontrer la superposition et l’intrication comme leviers d’un hashage probabilistique unique.

Produire un hash impossible à reconstituer sans le circuit quantique original, garantissant ainsi une sécurité post-quantique native.

Architecture du PoC

Le projet se décompose en 3 modules principaux :

Classical Input Layer
Le message à hasher est encodé en binaire (ASCII) puis converti en amplitudes quantiques dans un registre Qiskit.

Quantum Transformation Layer
Un ensemble d’opérations quantiques (Hadamard, Pauli-X, rotation et oracle) simule les différentes étapes du SHA-256, mais sur des états superposés.
Chaque itération introduit de l’entropie contrôlée via des portes quantiques aléatoires (RZ, RX) pour obtenir une signature unique.

Measurement & Collapse Layer
La mesure des qubits effondre la fonction de hashage, produisant un résultat final — une empreinte quantique non réversible.

Principe du hashage quantique

SHA-256 repose sur une succession de décalages et de modulos binaires.
SHA-666 applique des rotations quantiques aléatoires et un oracle non déterministe basé sur le principe d’incertitude.

Ainsi, la sortie d’un même input dépend :

de l’état quantique du processeur au moment du hash,

des paramètres aléatoires de phase,
