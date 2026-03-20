# Portfolio personnel de Jiahan Wang

Site personnel statique en francais, pense pour presenter un profil d'etudiant ingenieur oriente IA appliquee, RAG, vision embarquee et systemes connectes. Le projet a ete construit a partir du CV present dans ce dossier, avec un design sombre, sobre et moderne, pour etre heberge facilement sur GitHub ou deployee sur une instance AWS EC2.

## 1. Projet

- Stack : HTML, CSS, JavaScript vanilla
- Objectif : page personnelle rapide a charger, simple a modifier, sans build step
- Cible : GitHub, AWS EC2, lien de portfolio dans CV / LinkedIn / candidatures

Contenu principal du site :

- Hero avec positionnement personnel et CTA
- About me en francais
- Skills par categories
- Projects avec problemes, contribution, stack et impact
- Formation et experiences
- Contact

## 2. Lancer le site en local

Le projet est statique. Aucun `npm install` n'est necessaire.

Option simple :

```bash
cd /Users/asen/Desktop/presentation
python3 -m http.server 8080
```

Puis ouvrir :

```text
http://localhost:8080
```

## 3. Modifier le contenu

Les fichiers importants sont :

- `index.html` : structure de la page
- `assets/css/styles.css` : design, layout, responsive
- `assets/js/content.js` : contenu principal du site
- `assets/js/main.js` : rendu dynamique des cartes et interactions
- `deploy/nginx-personal-site.conf` : configuration nginx pour EC2
- `deploy/deploy-ec2.sh` : script d'upload/deploiement

Pour modifier rapidement les textes :

1. Ouvrir `assets/js/content.js`
2. Mettre a jour les sections `person`, `skills`, `projects`, `timeline`, `contact`
3. Recharger le navigateur

Notes de contenu a completer :

- Le lien LinkedIn est actuellement un placeholder : `linkedin.com/in/votre-profil`
- Le profil GitHub est initialise avec `github.com/wabo822`, deduit du depot fourni. Ajustez-le si besoin.

## 4. Deployer sur AWS EC2

Le site etant statique, le mode deploiement recommande est `nginx`.

### Prerequis

- Une instance EC2 Amazon Linux accessible en SSH
- Un groupe de securite ouvrant :
  - port `22` pour SSH
  - port `80` pour HTTP
  - port `443` pour HTTPS si vous ajoutez TLS ensuite
- Une cle SSH fonctionnelle sur votre machine

### Methode manuelle

1. Se connecter a la machine :

```bash
ssh -i /chemin/vers/votre-cle.pem ec2-user@VOTRE_IP_EC2
```

2. Installer nginx :

```bash
sudo dnf update -y
sudo dnf install -y nginx
sudo systemctl enable --now nginx
```

3. Copier le projet sur le serveur :

```bash
rsync -avz --delete \
  --exclude ".git" \
  --exclude ".DS_Store" \
  /Users/asen/Desktop/presentation/ \
  ec2-user@VOTRE_IP_EC2:/home/ec2-user/personal-site/
```

4. Publier les fichiers dans le web root :

```bash
ssh ec2-user@VOTRE_IP_EC2
sudo mkdir -p /var/www/personal-site
sudo rsync -av --delete /home/ec2-user/personal-site/ /var/www/personal-site/ \
  --exclude ".git" \
  --exclude ".DS_Store"
```

5. Installer la configuration nginx :

```bash
sudo cp /home/ec2-user/personal-site/deploy/nginx-personal-site.conf /etc/nginx/conf.d/personal-site.conf
sudo nginx -t
sudo systemctl reload nginx
```

6. Tester depuis un navigateur :

```text
http://VOTRE_IP_EC2
```

### Methode script

Le script `deploy/deploy-ec2.sh` automatise l'upload et la publication.

Exemple :

```bash
cd /Users/asen/Desktop/presentation
chmod +x deploy/deploy-ec2.sh
EC2_HOST=VOTRE_IP_EC2 ./deploy/deploy-ec2.sh
```

Pour un domaine :

```bash
EC2_HOST=VOTRE_IP_EC2 SERVER_NAME=portfolio.votredomaine.com ./deploy/deploy-ec2.sh
```

## 5. Lier un domaine

Etapes minimales :

1. Pointer un enregistrement `A` de votre domaine vers l'IP publique EC2
2. Remplacer `server_name _;` par votre domaine dans `deploy/nginx-personal-site.conf`
3. Recharger nginx :

```bash
sudo nginx -t
sudo systemctl reload nginx
```

4. Optionnel ensuite : ajouter HTTPS avec Let's Encrypt / Certbot

## Structure du projet

```text
.
├── index.html
├── README.md
├── cv_mars2026.pdf
├── assets
│   ├── css/styles.css
│   ├── icons/favicon.svg
│   └── js
│       ├── content.js
│       └── main.js
└── deploy
    ├── deploy-ec2.sh
    └── nginx-personal-site.conf
```
