gsap.registerPlugin(ScrollTrigger);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x3a0a0a);
scene.fog = new THREE.Fog(0x3a0a0a, 7, 30);
const camera = new THREE.PerspectiveCamera(70, innerWidth/innerHeight, 0.1, 100);
camera.position.set(0, 1.7, 10);
const renderer = new THREE.WebGLRenderer({antialias:true});
renderer.setSize(innerWidth, innerHeight);
document.body.appendChild(renderer.domElement);
const globalLight = new THREE.AmbientLight(0xffa500, 0.45);
scene.add(globalLight);
const ceilingLight = new THREE.DirectionalLight(0xffa500, 0.8);
ceilingLight.position.set(0, 4.7, 8);
ceilingLight.target.position.set(0, 2, -20);
scene.add(ceilingLight, ceilingLight.target);
const floor = new THREE.Mesh(new THREE.PlaneGeometry(6, 34), new THREE.MeshStandardMaterial({color:0x111111, metalness:0.28, roughness:0.24}));
floor.rotation.x = -Math.PI/2; floor.position.set(0,0,-2); scene.add(floor);
const wallMat = new THREE.MeshStandardMaterial({color:0x3a0a0a, emissive:0x000000, emissiveIntensity:0, roughness:0.82, metalness:0});
const leftWall = new THREE.Mesh(new THREE.BoxGeometry(0.4,5,34), wallMat); leftWall.position.set(-3.2,2.5,-2); scene.add(leftWall);
const rightWall = new THREE.Mesh(new THREE.BoxGeometry(0.4,5,34), wallMat); rightWall.position.set(3.2,2.5,-2); scene.add(rightWall);
const ceil = new THREE.Mesh(new THREE.BoxGeometry(7,0.4,34), new THREE.MeshStandardMaterial({color:0x000000, roughness:0.95})); ceil.position.set(0,4.8,-2); scene.add(ceil);

function makeTableau(title, sub, color, side, z){
  const x = side === 'left' ? -2.95 : 2.95;
  const canvas = document.createElement('canvas'); canvas.width=512; canvas.height=320;
  const ctx = canvas.getContext('2d');
  ctx.fillStyle='#0a0a0a'; ctx.fillRect(0,0,512,320);
  ctx.fillStyle=color; ctx.font='bold 28px Arial'; ctx.fillText(title, 20, 55);
  ctx.fillStyle='#F5EFE6'; ctx.font='17px Arial'; ctx.fillText(sub, 20, 95);
  ctx.fillStyle=color; ctx.fillRect(20,125,280,6);
  ctx.fillStyle='#bbb'; ctx.font='15px Arial'; ctx.fillText('Fait par Fortuno_dev_IA', 20, 170);
  ctx.fillStyle='#F5EFE6'; ctx.font='bold 19px Arial'; ctx.fillText('VOIR LE PROJET', 20, 250);
  const tex = new THREE.CanvasTexture(canvas);
  const group = new THREE.Group();
  const frameMaterial = new THREE.MeshStandardMaterial({color:0xffd700, emissive:0x000000, metalness:0.7, roughness:0.3});
  const frame = new THREE.Mesh(new THREE.BoxGeometry(2.6,1.8,0.08), frameMaterial);
  const img = new THREE.Mesh(new THREE.PlaneGeometry(2.4,1.6), new THREE.MeshBasicMaterial({map:tex}));
  frame.userData.tableauGroup = null;
  img.userData.tableauGroup = null;
  if(side === 'left'){ group.rotation.y = Math.PI/2; } else { group.rotation.y = -Math.PI/2; }
  group.add(frame); img.position.z = 0.06; group.add(img);
  group.position.set(x, 2.1, z);
  group.userData = {title, desc:sub, project:projectData.find(p=>p.title===title), frameMaterial};
  frame.userData.tableau = group;
  img.userData.tableau = group;
  scene.add(group); return group;
}

// PROJETS RÉELS DU DOSSIER LOCAL
const projectData = [
  {id:'defaut-paiement',title:'DÉFAUT DE PAIEMENT',sub:'Prédiction + explication SHAP',color:'#ff8c00',side:'left',z:6,type:'ml',graphs:[
    ['Première lecture des données','mes_projets_previsions_non_paiement_risque_de_non_paiement_cell2_out0.png','Cible déséquilibrée : les défauts restent minoritaires. Le FICO est décalé selon le risque.'],
    ['ROC + Precision-Recall','mes_projets_previsions_non_paiement_risque_de_non_paiement_cell4_out0.png','Seuil F1 optimal 0.207, F1 0.348, précision défaut 0.29, rappel défaut 0.43 et accuracy 0.74.'],
    ['Variables importantes','mes_projets_previsions_non_paiement_risque_de_non_paiement_cell6_out0.png','Revenu annuel, objet du prêt, réclamations et mensualité sont les principales variables.'],
    ['Effet revenu et FICO','mes_projets_previsions_non_paiement_risque_de_non_paiement_cell7_out0.png','Le risque tend à diminuer lorsque le revenu annuel et le FICO augmentent.'],
    ['Dossier à risque','mes_projets_previsions_non_paiement_risque_de_non_paiement_cell9_out0.png','Montant impayé, objet « small_business » et revenu expliquent principalement la prédiction risquée.'],
    ['Calibration','mes_projets_previsions_non_paiement_risque_de_non_paiement_cell10_out0.png','La courbe suit globalement la diagonale. Le modèle reste fiable mais les probabilités doivent être interprétées prudemment.'] ]},
  {id:'titanic',title:'TITANIC',sub:'Régression logistique',color:'#FFA500',side:'right',z:2,type:'ml',graphs:[['Matrice de confusion + ROC','mes_projets_previsions_titanic_Regression_logistique_cell19_out0.png','137 décédés correctement prédits, 23 faux survivants, 75 survivants correctement prédits et 32 faux décédés. Accuracy 0.79, AUC 0.85.']]},
  {id:'vin',title:'CLASSIFICATION DES VINS',sub:'SVM + PCA',color:'#f2b84b',side:'left',z:-2,type:'ml',graphs:[
    ['Matrice de confusion','mes_projets_predictions_vins_SVM_cell19_out0.png','Lecture des classes correctement prédites et des confusions entre les catégories.'],
    ['Projection PCA','mes_projets_predictions_vins_SVM_cell19_out1.png','Projection des observations en deux dimensions pour visualiser la séparation des classes.'],
    ['Classes réelles / prédites','mes_projets_predictions_vins_SVM_cell19_out2.png','Comparaison visuelle entre les classes observées et les prédictions SVM.'],
    ['Optimisation C / gamma','mes_projets_predictions_vins_SVM_cell19_out4.png','Carte thermique des scores selon les hyperparamètres C et gamma.']]},
  {id:'vision',title:'VISION PAR ORDINATEUR',sub:'Robot + MediaPipe',color:'#FFA500',side:'right',z:-6,type:'video',video:'mes_projets/projet_vision_par_ordinateur/FORTUNO_ROBOT.mp4'},
  {id:'sayen',title:'FORTUNO SAYEN',sub:'Gestes + effets 3D',color:'#ffd166',side:'left',z:-10,type:'video',video:'mes_projets/projet_vision_par_ordinateur/Fortuno_sayen.mp4'},
  {id:'eduquiz',title:'EDUQUIZ AI',sub:'QCM IA depuis PDF',color:'#FFA500',side:'right',z:-14,type:'eduquiz'},
  {id:'conduite',title:'FORTUNO CONDUITE IA',sub:'Deep Q-Learning',color:'#FFA500',side:'right',z:-18,type:'video',video:'mes_projets/fortuno_conduit/Fortuno_conduit.mp4'},
  {id:'sql',title:'SQL — RÉSERVATION DE VOLS',sub:'Requêtes, vols, passagers',color:'#FFA500',side:'left',z:-22,type:'sql'},
  {id:'p02',title:'COUPE DU MONDE 2026',sub:'Prédiction des résultats',color:'#FFA500',side:'right',z:-26,type:'web'},
  {id:'p03',title:'TOUR DE FRANCE 2027',sub:'Clustering des villages',color:'#df9b55',side:'left',z:-30,type:'web'},
  {id:'rag',title:'HÔTEL RAG — ASSISTANT PDF',sub:'Recherche sémantique et IA',color:'#FFA500',side:'right',z:-34,type:'web',file:'mes_projets/cahier_vacances-FORTUNO-IA/Projet_04/projet_04.ipynb'},
  {id:'p06',title:'PRÉVISION DES VENTES DE GLACES',sub:'Séries temporelles ARMA',color:'#d5a85a',side:'left',z:-38,type:'web'},
  {id:'agent-voyage',title:'AGENT IA — PLANNIFICATEUR DE VOYAGE',sub:'Vols, hôtels, activités, budget',color:'#FFA500',side:'right',z:-42,type:'web',file:'mes_projets/cahier_vacances-FORTUNO-IA/Projet_07/projet_07.ipynb'}
];
const projects = projectData.map(p=>makeTableau(p.title,p.sub,p.color,p.side,p.z));
const endCanvas=document.createElement('canvas');endCanvas.width=512;endCanvas.height=320;const endCtx=endCanvas.getContext('2d');endCtx.fillStyle='#3A0A0A';endCtx.fillRect(0,0,512,320);endCtx.strokeStyle='#FFD700';endCtx.lineWidth=8;endCtx.strokeRect(12,12,488,296);
const endWall=new THREE.Mesh(new THREE.PlaneGeometry(2.6,1.8),new THREE.MeshBasicMaterial({map:new THREE.CanvasTexture(endCanvas)}));endWall.position.set(0,2.25,-45);scene.add(endWall);

let activeProject=null;
const detail=document.getElementById('projectDetail'),detailContent=document.getElementById('detailContent');
function mlDetail(p){return `<h2>${p.title}</h2><p>${p.sub}</p><div class="detail-grid">${p.graphs.map((g,i)=>`<article><img src="assets/graphs/${g[1]}" alt="${g[0]}"><h3>Graphe ${i+1} — ${g[0]}</h3><p>${g[2]}</p></article>`).join('')}</div>`}
function videoDetail(p){const robot=p.title.includes('VISION');return `<h2>${p.title}</h2><p>${p.sub}</p><div class="detail-video"><video controls src="${p.video}"></video></div><div class="detail-info"><article><strong>Fonctionnement</strong><span>${robot?'Détection du corps, du visage et des gestes en temps réel.':'Observation des obstacles et choix d’une action par apprentissage par renforcement.'}</span></article><article><strong>Localisation</strong><span>${robot?'MediaPipe + scène 3D':'Simulation de conduite autonome'}</span></article></div>`}
function aboutDetail(){
  detailContent.innerHTML=`<div class="about-detail">
    <section class="about-hero">
      <img src="fortuno1.jpeg" alt="BAGAYOKO ABOULAYE — Fortuno Dev IA">
      <div><span class="about-eyebrow">À propos</span><h2>BAGAYOKO ABOULAYE</h2><div class="identity">FORTUNO_DEV_IA</div><p class="intro">Étudiant en informatique en Côte d’Ivoire, je transforme ce que j’apprends en projets utiles autour de l’intelligence artificielle.</p></div>
    </section>
    <section class="about-proof"><article><strong>2025</strong><span>Baccalauréat série C</span></article><article><strong>IA & Robotique</strong><span>Formation à l’UVCI</span></article><article><strong>MIAGE</strong><span>L2 à l’UPB</span></article></section>
    <section class="about-story">
      <div class="section-heading"><span>01</span><h3>Mon parcours</h3></div>
      <article><strong>Le point de départ</strong><p>Après mon bac C, je savais déjà vers quoi je voulais avancer : l’informatique et, plus précisément, l’intelligence artificielle.</p></article>
      <article><strong>Le détour</strong><p>À l’UFHB, j’ai suivi un temps le parcours Math-Info sur les conseils d’un aîné. Cette expérience m’a aidé à comprendre qu’une autre voie me convenait mieux. Le choix de changer m’a fait hésiter, mais il a aussi clarifié mon projet.</p></article>
      <article><strong>Le nouveau départ</strong><p>Je me suis tourné vers l’UVCI pour apprendre l’intelligence artificielle et la robotique, tout en poursuivant une L2 MIAGE à l’UPB.</p></article>
      <article><strong>Ma façon d’apprendre</strong><p>J’apprends en construisant : scraping, analyse de données, réseaux de neurones, applications web, bots et vision par ordinateur.</p></article>
    </section>
    <section class="about-skills"><div class="section-heading"><span>02</span><h3>Ce que je pratique</h3></div><div class="skill-list"><span>Python</span><span>Django</span><span>Data Science</span><span>Machine Learning</span><span>Node.js</span><span>IA générative</span><span>SQL</span><span>Vision par ordinateur</span><span>MediaPipe</span><span>Scraping</span><span>Streamlit</span></div></section>
    <section class="about-gallery"><div class="section-heading"><span>03</span><h3>En images</h3></div><div class="about-gallery-grid"><img src="fortuno1.jpeg" alt="BAGAYOKO ABOULAYE"><img src="fortuno2.jpeg" alt="Fortuno au travail"><img src="fortuno3.jpeg" alt="FORTUNO_DEV_IA"></div></section>
    <section class="about-certificate"><div class="section-heading"><span>04</span><h3>Mon certificat</h3></div><a href="mon_certificat.png" target="_blank" rel="noopener"><img src="mon_certificat.png" alt="Certificat de Fortuno Dev IA"><span>Ouvrir le certificat ↗</span></a></section>
    <footer class="about-footer"><div><strong>BAGAYOKO ABOULAYE</strong><span>Abidjan, Côte d’Ivoire</span></div><a href="mailto:presidentfortuno@gmail.com">Me contacter</a></footer>
  </div>`;
  detail.classList.add('open'); detail.style.display='block'; detail.scrollTop=0;
}
function openDetail(p){activeProject=p;let body='';if(p.type==='ml')body=mlDetail(p);else if(p.type==='video')body=videoDetail(p);else if(p.type==='sql')body=`<h2>${p.title}</h2><p>${p.sub}</p><div class="detail-info"><article><strong>15</strong><span>Passagers</span></article><article><strong>15</strong><span>Vols</span></article><article><strong>19</strong><span>Réservations</span></article><article><strong>SQLite</strong><span>Base relationnelle</span></article></div><div class="detail-demo"><h3>Requête</h3><pre>SELECT flight_number, destination, price_eur\nFROM flights\nWHERE price_eur &gt; (SELECT AVG(price_eur) FROM flights)\nORDER BY price_eur DESC;</pre><table><thead><tr><th>Résultat attendu</th><th>Critère</th></tr></thead><tbody><tr><td>Vols filtrés</td><td>Prix supérieur à la moyenne</td></tr></tbody></table></div>`;else if(p.type==='eduquiz')body=`<h2>${p.title}</h2><p>Application Django qui extrait le contenu de PDF et génère des QCM, résumés et corrections.</p><div class="detail-demo"><h3>Démonstration du QCM</h3><pre>1. Quelle technologie extrait le texte du document ?\nA. Extraction côté application  ✓\nB. Capture vidéo\nC. Stockage sans lecture</pre></div><div class="detail-info"><article><strong>Django</strong><span>Application web</span></article><article><strong>PDF</strong><span>Extraction de contenu</span></article></div>`;else body=`<h2>${p.title}</h2><p>${p.sub}</p><div class="detail-info"><article><strong>Dashboard</strong><span>Graphiques, résultats et interprétation</span></article></div>`;detailContent.innerHTML=body;detail.classList.add('open')}
document.querySelector('.close-detail').addEventListener('click',()=>{detail.classList.remove('open');detail.style.display='none';});document.getElementById('cardButton').onclick=()=>{if(activeProject)location.href=`projet.html?project=${activeProject.id}`};
const raycaster=new THREE.Raycaster(),mouse=new THREE.Vector2();
renderer.domElement.addEventListener('click',e=>{mouse.x=e.clientX/innerWidth*2-1;mouse.y=-(e.clientY/innerHeight)*2+1;raycaster.setFromCamera(mouse,camera);const hit=raycaster.intersectObjects(projects,true)[0];if(hit){let g=hit.object;while(g&&(!g.userData||!g.userData.project))g=g.parent;if(g&&g.userData.project){firstGuided=false;location.href=`projet.html?project=${g.userData.project.id}`}}});
gsap.to(camera.position, {
  z: -42, ease:'none',
  scrollTrigger:{trigger:'.scroll', start:'top top', end:'bottom bottom', scrub:1,
    onUpdate: self=>{
      const p=self.progress,idx=Math.min(projectData.length-1,Math.floor(p*projectData.length));activeProject=projectData[idx];document.getElementById('intro').style.opacity=String(1-p*4);const card=document.getElementById('card');if(p>.035&&p<.97){card.style.display='block';document.getElementById('cardTitle').innerText=activeProject.title;document.getElementById('cardText').innerText=activeProject.sub}else card.style.display='none';
    }
  }
});
let firstGuided=true;
const fixture=document.getElementById('lightFixture');
const bulb=fixture.querySelector('.bulb');
let lightOn=false;
bulb.addEventListener('click',e=>{e.stopPropagation();lightOn=!lightOn;fixture.classList.toggle('light-on',lightOn);document.body.classList.toggle('chateau-lit',lightOn);globalLight.intensity=lightOn?1.15:0.45;ceilingLight.intensity=lightOn?1.35:0.8;wallMat.emissive.setHex(lightOn?0x8b3f00:0x000000);wallMat.emissiveIntensity=lightOn?0.16:0;projects.forEach(p=>{if(p.userData.frameMaterial)p.userData.frameMaterial.emissive.setHex(lightOn?0xffa500:0x000000);p.userData.frameMaterial.emissiveIntensity=lightOn?0.28:0;});});

const welcome=document.getElementById('welcomeGuide');
welcome.classList.add('welcome-show');setTimeout(()=>welcome.classList.remove('welcome-show'),5000);

const dust=document.getElementById('dust');
for(let i=0;i<28;i++){const p=document.createElement('i');p.style.left=`${8+Math.random()*84}%`;p.style.setProperty('--dur',`${8+Math.random()*12}s`);p.style.setProperty('--dx',`${-35+Math.random()*70}px`);p.style.animationDelay=`-${Math.random()*18}s`;dust.appendChild(p)}

const plan=document.getElementById('projectPlan');
const planItems=[...projectData,{id:'apropos',title:'À PROPOS'}];
planItems.forEach((p,i)=>{const b=document.createElement('button');b.className='plan-dot'+(i===0?' active':'');b.type='button';b.innerHTML=`<span>${p.title}</span>`;b.addEventListener('click',()=>{const sc=document.querySelector('.scroll');const max=Math.max(0,sc.offsetHeight-innerHeight);if(p.id==='apropos'){activeProject=null;aboutDetail()}else{const idx=projectData.findIndex(x=>x.id===p.id);const y=sc.offsetTop+(idx/(projectData.length-1))*max;window.scrollTo({top:y,behavior:'smooth'});}});if(p.id==='apropos')b.setAttribute('onclick','aboutDetail()');plan.appendChild(b)});
const aboutPlanButton=plan.querySelector('.plan-dot:last-child');if(aboutPlanButton)aboutPlanButton.addEventListener('click',()=>{activeProject=null;aboutDetail();});
function setActiveDot(idx){document.querySelectorAll('.plan-dot').forEach((b,i)=>b.classList.toggle('active',i===idx));}
function updateActiveDot(){const sc=document.querySelector('.scroll');const max=Math.max(0,sc.offsetHeight-innerHeight);const limit=sc.offsetTop+max;if(window.innerWidth>=768&&scrollY>limit)window.scrollTo({top:limit,behavior:'auto'});const progress=Math.max(0,Math.min(1,(scrollY-sc.offsetTop)/max));const idx=Math.round(progress*(projectData.length-1));setActiveDot(idx);document.getElementById('endWallOverlay').classList.toggle('show',progress>=.94)}
addEventListener('scroll',updateActiveDot,{passive:true});updateActiveDot();

document.querySelector('.returnCastle').addEventListener('click',()=>window.scrollTo({top:0,behavior:'smooth'}));
addEventListener('keydown',e=>{if(e.key==='Escape'){window.scrollTo({top:0,behavior:'smooth'});setActiveDot(0)}else if(e.key==='ArrowRight'||e.key==='ArrowLeft'){const sc=document.querySelector('.scroll');const max=Math.max(0,sc.offsetHeight-innerHeight);const progress=Math.max(0,Math.min(1,(scrollY-sc.offsetTop)/max));let idx=Math.round(progress*(projectData.length-1));idx=Math.max(0,Math.min(projectData.length-1,idx+(e.key==='ArrowRight'?1:-1)));const y=sc.offsetTop+(idx/(projectData.length-1))*max;window.scrollTo({top:y,behavior:'smooth'});setActiveDot(idx)}});

const mobile=document.getElementById('mobileCastle');
const mobileCovers={
  eduquiz:'mes_projets/Eduquiz-AI/eduquiz1.png',
  sql:'mes_projets/cahier_vacances-FORTUNO-IA/Projet_01/base_de_données.png',
  p03:'mes_projets/cahier_vacances-FORTUNO-IA/Projet_03/villages_map.png',
  rag:"mes_projets/cahier_vacances-FORTUNO-IA/Projet_04/l'interface_hotel_belvedere.png",
  'agent-voyage':'mes_projets/cahier_vacances-FORTUNO-IA/Projet_07/architecture.png'
};
projectData.forEach((p,i)=>{
  const card=document.createElement('article');
  card.className='mobile-card';
  const image=p.graphs&&p.graphs.length
    ?`assets/graphs/${p.graphs[0][1]}`
    :(mobileCovers[p.id]||null);
  const visual=image
    ?`<img src="${image}" alt="Illustration du projet ${p.title}">`
    :`<div class="mobile-project-cover" aria-label="${p.title}"><span>${String(i+1).padStart(2,'0')}</span><strong>${p.title}</strong><em>${p.sub}</em></div>`;
  card.innerHTML=`${visual}<div><h2>${p.title}</h2><p>${p.sub}</p><a href="projet.html?project=${p.id}">VOIR LE PROJET →</a></div>`;
  mobile.appendChild(card);
});
const aboutCard=document.createElement('article');aboutCard.className='mobile-card';aboutCard.innerHTML=`<img src="fortuno1.jpeg" alt="BAGAYOKO ABOULAYE"><div><h2>À PROPOS DE MOI</h2><p>Mon histoire, mes compétences et mon certificat.</p><a href="#" onclick="aboutDetail();return false">VOIR À PROPOS →</a></div>`;mobile.appendChild(aboutCard);
const socialIcon={email:`<svg class="social-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M2 4h20v16H2V4zm2 2v.5l8 5.5 8-5.5V6H4zm16 3.2-8 5.5-8-5.5V18h16v-8.8z"/></svg>`,linkedin:`<svg class="social-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M20.45 20.45h-3.56v-5.57c0-1.33-.02-3.04-1.85-3.04-1.85 0-2.14 1.45-2.14 2.94v5.67H9.35V9h3.41v1.56h.05c.47-.9 1.64-1.85 3.37-1.85 3.6 0 4.27 2.37 4.27 5.46v6.28zM5.34 7.43a2.06 2.06 0 110-4.12 2.06 2.06 0 010 4.12zm1.78 13.02H3.56V9h3.56v11.45zM22.23 0H1.77C.79 0 0 .77 0 1.73v20.54C0 23.23.79 24 1.77 24h20.46c.98 0 1.77-.77 1.77-1.73V1.73C24 .77 23.21 0 22.23 0z"/></svg>`,tiktok:`<svg class="social-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M16.6 2c.2 1.6 1.1 3 2.5 3.9.9.5 1.9.8 3 .8v4c-1.9.1-3.7-.5-5.2-1.5v6.4c0 3.6-2.9 6.4-6.4 6.4S4 18.9 4 15.6s2.9-6.4 6.4-6.4c.4 0 .8 0 1.2.1v4a3.9 3.9 0 00-1.2-.2 2.5 2.5 0 100 5 2.5 2.5 0 002.5-2.5V2h3.7z"/></svg>`,facebook:`<svg class="social-icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M24 12.07C24 5.41 18.63 0 12 0S0 5.41 0 12.07C0 18.09 4.39 23.08 10.13 24v-8.44H7.08v-3.49h3.05V9.37c0-3.04 1.79-4.72 4.53-4.72 1.31 0 2.68.24 2.68.24v2.98h-1.51c-1.49 0-1.96.93-1.96 1.89v2.31h3.33l-.53 3.49h-2.8V24C19.61 23.08 24 18.09 24 12.07z"/></svg>`};
const mobileEnd=document.createElement('article');mobileEnd.className='mobile-card mobile-end';mobileEnd.innerHTML=`<div><h2>MERCI DE TA VISITE</h2><p class="mobile-name">FORTUNO DEV IA</p><p>Contact : presidentfortuno@gmail.com</p><nav class="mobile-socials"><a href="mailto:presidentfortuno@gmail.com">${socialIcon.email}<span>M&apos;ENVOYER UN EMAIL</span></a><a href="https://www.linkedin.com/in/fortuno-dev-ia-0a419a246" target="_blank" rel="noopener">${socialIcon.linkedin}<span>MON LINKEDIN</span></a><a href="https://www.tiktok.com/@presidentfortuno" target="_blank" rel="noopener">${socialIcon.tiktok}<span>MON TIKTOK</span></a><a href="https://www.facebook.com/share/1Q5naPUV8s/?mibextid=wwXIfr" target="_blank" rel="noopener">${socialIcon.facebook}<span>MON FACEBOOK</span></a></nav><button type="button" onclick="window.scrollTo({top:0,behavior:'smooth'})">← RETOUR À L&apos;ENTRÉE</button></div>`;mobile.appendChild(mobileEnd);

let hoverGroup=null;
const hoverLabel=document.getElementById('projectHoverLabel');
renderer.domElement.addEventListener('mousemove',e=>{mouse.x=e.clientX/innerWidth*2-1;mouse.y=-(e.clientY/innerHeight)*2+1;raycaster.setFromCamera(mouse,camera);const hit=raycaster.intersectObjects(projects,true)[0];let next=null;if(hit){let g=hit.object;while(g&&!g.userData.project)g=g.parent;if(g&&g.userData.project)next=g;}if(hoverGroup&&hoverGroup!==next){hoverGroup.scale.set(1,1,1);if(hoverGroup.userData.frameMaterial)hoverGroup.userData.frameMaterial.emissive.set(0x000000)}hoverGroup=next;if(next){next.scale.set(1.1,1.1,1.1);if(next.userData.frameMaterial)next.userData.frameMaterial.emissive.set(0x5c3a00);hoverLabel.classList.add('show');hoverLabel.style.left=`${e.clientX+18}px`;hoverLabel.style.top=`${e.clientY-38}px`}else{hoverLabel.classList.remove('show')}});
renderer.domElement.addEventListener('mouseleave',()=>{if(hoverGroup){hoverGroup.scale.set(1,1,1);hoverGroup.userData.frameMaterial&&hoverGroup.userData.frameMaterial.emissive.set(0x000000)}hoverGroup=null;hoverLabel.classList.remove('show')});

function animate(){requestAnimationFrame(animate);if(firstGuided&&projects[0]){const s=1.06+Math.sin(performance.now()*0.004)*0.025;projects[0].scale.set(s,s,s);projects[0].userData.frameMaterial.emissive.setHex(Math.floor(performance.now()/220)%2?0xff6a00:0x4a2200)}renderer.render(scene,camera)}
animate();
addEventListener('resize',()=>{camera.aspect=innerWidth/innerHeight;camera.updateProjectionMatrix();renderer.setSize(innerWidth,innerHeight)});
