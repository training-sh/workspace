"""Original course diagrams. Run with Python and Pillow >= 10.1; no network needed.

SVG originals and 2400 x 1440 PNGs share the same drawing instructions.
No external logos, photographs, fonts or runtime services are required.
"""
from pathlib import Path
from html import escape
import json
import math
import re
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent
W, H, SCALE = 1200, 720, 2
INK, MUTED, LINE = '#172b4d', '#526581', '#cbd5e1'
BLUE, GREEN, PURPLE, AMBER = '#2563eb', '#087f5b', '#7047bd', '#ad6200'
PALE = {BLUE: '#edf4ff', GREEN: '#e9f7f0', PURPLE: '#f3effb', AMBER: '#fff6e7'}


def font(size, bold=False):
    candidates = [
        Path('C:/Windows/Fonts') / ('segoeuib.ttf' if bold else 'segoeui.ttf'),
        Path('/usr/share/fonts/truetype/dejavu') / ('DejaVuSans-Bold.ttf' if bold else 'DejaVuSans.ttf'),
    ]
    for p in candidates:
        if p.exists():
            return ImageFont.truetype(str(p), size * SCALE)
    return ImageFont.load_default(size=size * SCALE)


class Figure:
    def __init__(self, name, title, subtitle):
        self.name = name
        self.image = Image.new('RGB', (W * SCALE, H * SCALE), '#f8fafc')
        self.draw = ImageDraw.Draw(self.image)
        self.svg = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" role="img" aria-labelledby="title desc">',
                    f'<title id="title">{escape(title)}</title><desc id="desc">{escape(subtitle)}</desc>',
                    '<rect width="1200" height="720" fill="#f8fafc"/>']
        self.text(50, 35, 'KUBERNETES / VISUAL GUIDE', 15, BLUE, True)
        self.text(50, 65, title, 34, INK, True)
        self.text(50, 116, subtitle, 19, MUTED)

    def rect(self, x, y, w, h, fill='white', stroke=LINE, radius=16):
        assert 0 <= x <= W and 0 <= y <= H and x + w <= W and y + h <= H
        self.draw.rounded_rectangle((x*SCALE, y*SCALE, (x+w)*SCALE, (y+h)*SCALE), radius=radius*SCALE, fill=fill, outline=stroke, width=2*SCALE)
        self.svg.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="2"/>')

    def text(self, x, y, value, size=20, color=INK, bold=False, center=False):
        f = font(size, bold)
        width = self.draw.textlength(value, font=f) / SCALE
        assert x - (width/2 if center else 0) >= 0 and x + (width/2 if center else width) <= W, (self.name, value, width)
        self.draw.text((x*SCALE, y*SCALE), value, font=f, fill=color, anchor='mt' if center else 'lt')
        self.svg.append(f'<text x="{x}" y="{y+size*.82}" fill="{color}" font-family="Segoe UI, DejaVu Sans, Arial, sans-serif" font-size="{size}" font-weight="{700 if bold else 400}" text-anchor="{"middle" if center else "start"}">{escape(value)}</text>')

    def box(self, x, y, w, h, title, lines=(), color=BLUE, size=19):
        self.rect(x, y, w, h, PALE[color], color)
        title_size = 22
        while title_size > 17 and self.draw.textlength(title, font=font(title_size, True)) / SCALE > w-36:
            title_size -= 1
        assert self.draw.textlength(title, font=font(title_size, True)) / SCALE <= w-36, (self.name, title, w)
        self.text(x+18, y+17, title, title_size, color, True)
        for i, line in enumerate(lines):
            assert self.draw.textlength(line, font=font(size)) / SCALE <= w-36, (self.name, line, w)
            self.text(x+18, y+53+i*28, line, size)

    def arrow(self, points, color=MUTED, width=3):
        coords = [(int(x*SCALE), int(y*SCALE)) for x, y in points]
        self.draw.line(coords, fill=color, width=width*SCALE)
        x, y = points[-1]; x0, y0 = points[-2]
        angle = math.atan2(y-y0, x-x0)
        head = [(x, y), (x-11*math.cos(angle-.48), y-11*math.sin(angle-.48)), (x-11*math.cos(angle+.48), y-11*math.sin(angle+.48))]
        self.draw.polygon([(int(a*SCALE), int(b*SCALE)) for a, b in head], fill=color)
        self.svg.append(f'<polyline points="{" ".join(f"{a},{b}" for a,b in points)}" fill="none" stroke="{color}" stroke-width="{width}" stroke-linejoin="round"/>')
        self.svg.append(f'<polygon points="{" ".join(f"{a:.1f},{b:.1f}" for a,b in head)}" fill="{color}"/>')

    def footer(self, value):
        self.rect(50, 659, 1100, 42, '#eaf0f7', '#eaf0f7', 10)
        self.text(70, 669, value, 17, MUTED)

    def save(self):
        self.svg.append('</svg>')
        (ROOT / (self.name+'.svg')).write_text('\n'.join(self.svg)+'\n', encoding='utf-8')
        self.image.save(ROOT / (self.name+'.png'), optimize=True)


def render():
    f = Figure('01-docker-compose-kubernetes', 'From one container to a managed application', 'The image can stay the same. The way you manage its running copies changes.')
    for x, title, lines, color in [
        (50, 'Docker Engine', ['Package and run containers', 'on a chosen host.'], BLUE),
        (425, 'Docker Compose', ['Describe a multi-container', 'application on a Docker host.'], PURPLE),
        (800, 'Kubernetes', ['Declare desired state;', 'controllers keep reconciling it.'], GREEN)]:
        f.box(x, 180, 350, 440, title, lines, color)
    f.box(80, 340, 290, 95, 'Image', ['Reusable application package'])
    f.arrow([(225,435),(225,465)], BLUE)
    f.box(80, 465, 290, 95, 'Container', ['A running instance'])
    for x, label in [(450,'web'),(615,'database')]:
        f.box(x, 350, 135, 105, label, ['Container'], PURPLE, 17)
    f.box(455, 480, 290, 80, 'Compose project', [], PURPLE)
    for x, label in [(825,'Node A'),(990,'Node B')]:
        f.box(x, 350, 135, 105, label, ['Pods'], GREEN, 17)
    f.box(830, 480, 290, 80, 'Controllers + API', [], GREEN)
    f.footer('Compose can restart and scale containers locally. Kubernetes adds cluster-wide scheduling and reconciliation.')
    f.save()

    f = Figure('02-images-and-runtimes', 'Image, container and runtime are different things', 'Docker-built compatible images can run under containerd in Kubernetes.')
    f.box(50,185,270,150,'Build',['Dockerfile + application','docker build'],BLUE)
    f.box(460,185,270,150,'Image',['Layers + configuration','Tag or immutable digest'],PURPLE)
    f.box(870,185,280,150,'Registry',['Store and distribute images','Private or public'],AMBER)
    f.arrow([(320,260),(460,260)]); f.arrow([(730,260),(870,260)])
    f.text(360,225,'build',18,MUTED); f.text(772,225,'push',18,MUTED)
    f.box(50,420,270,165,'Kubelet',['Reads assigned Pod spec','Calls the runtime via CRI'],BLUE)
    f.box(460,420,270,165,'containerd',['Pulls/manages images','Starts containers via runc'],PURPLE)
    f.box(870,420,280,165,'Pod',['Running container(s)','Using the selected image'],GREEN)
    f.arrow([(320,500),(460,500)]); f.arrow([(730,500),(870,500)])
    f.arrow([(1010,335),(1010,380),(600,380),(600,420)],AMBER)
    f.text(750,354,'pull image',18,AMBER)
    f.footer('A tag is a label that can move. A digest identifies exact image content. A container is a runtime instance.')
    f.save()

    f = Figure('03-cluster-architecture', 'Who does what inside a Kubernetes cluster?', 'The control plane coordinates. Node components run and connect Pods.')
    f.box(50,175,480,80,'kubectl / UI / automation',[],PURPLE)
    f.arrow([(290,255),(290,315)],PURPLE); f.text(310,273,'API requests',17,PURPLE)
    f.rect(50,290,480,340,'white',BLUE)
    f.text(70,303,'CONTROL PLANE',16,BLUE,True)
    f.box(75,345,430,90,'API server',['The shared entry point'],BLUE)
    for x,w,title,lines in [(75,125,'etcd',['Cluster','state']), (215,135,'Scheduler',['Chooses','a node']), (365,140,'Controllers',['Reconcile','objects'])]:
        f.box(x,500,w,105,title,lines,BLUE,17)
    f.arrow([(137,435),(137,500)]); f.arrow([(282,500),(282,435)]); f.arrow([(435,500),(435,435)])
    f.rect(620,290,530,340,'white',GREEN)
    f.text(640,303,'WORKER NODE',16,GREEN,True)
    f.box(645,345,480,90,'Kubelet',['Watches assignments; reports status'],GREEN)
    f.arrow([(505,385),(645,385)],BLUE); f.text(548,358,'API',16,BLUE)
    f.box(645,475,210,125,'containerd',['CRI runtime','Runs containers'],PURPLE,18)
    f.box(910,475,215,125,'Pods',['Application','container(s)'],GREEN)
    f.arrow([(745,435),(745,475)],GREEN); f.arrow([(855,537),(910,537)])
    f.footer('CoreDNS handles service names. A CNI plugin handles Pod networking. Service routing also needs a data plane.')
    f.save()

    f = Figure('04-inside-a-pod', 'A Pod is the unit Kubernetes places on a node', 'One app container is common. Add a sidecar only when it belongs in the same Pod.')
    f.rect(50,185,550,435,'white',GREEN)
    f.text(75,205,'POD: one scheduling and network unit',23,GREEN,True)
    f.box(75,270,235,140,'App container',['Runs the application','Reads/writes shared files'],BLUE,18)
    f.box(335,270,240,140,'Sidecar',['Example: forwards logs','Has its own resources'],PURPLE,18)
    f.box(75,445,500,75,'One Pod IP + shared localhost',[],GREEN)
    f.box(75,550,500,50,'A volume can be mounted by both containers',[],AMBER)
    f.arrow([(193,410),(193,445)]); f.arrow([(455,410),(455,445)])
    f.box(650,185,500,170,'What is shared?',['Network namespace and Pod IP','Declared volumes, when mounted','Containers keep separate image filesystems'],GREEN)
    f.box(650,385,500,235,'What is not a replica?',['App + sidecar = one Pod, not two replicas.','Two independent app copies = two Pods.','Frontend and database usually use','separate Pods and Services.'],BLUE)
    f.footer('A replacement Pod has a new identity and usually a new IP. Put persistent application data on suitable storage.')
    f.save()

    f = Figure('05-desired-state', 'Desired state is a continuing instruction', 'Example: keep three application Pods available, even as individual Pods disappear.')
    f.box(50,185,300,135,'Deployment spec',['replicas: 3','Image + Pod template'],BLUE,18)
    f.box(460,185,300,135,'Controller + ReplicaSet',['Compare spec with current state','Create replacement Pods'],PURPLE,18)
    f.arrow([(350,255),(460,255)])
    for x,title,color in [(50,'Pod A: ready',GREEN),(460,'Pod B: lost',AMBER),(870,'Pod C: ready',GREEN)]:
        f.box(x,385,280,95,title,[],color)
    f.arrow([(610,385),(610,320)],PURPLE)
    f.box(460,530,300,90,'New Pod B2: ready',[],GREEN)
    f.arrow([(460,285),(405,285),(405,575),(460,575)],GREEN)
    f.text(810,555,'New Pod, possibly a new node/IP',18,MUTED)
    f.footer('Container restart and Pod replacement differ. Recovery still needs healthy capacity, networking and accessible data.')
    f.save()

    f = Figure('06-services-and-access', 'A Service gives changing Pods a stable address', 'Selectors choose the Pods. Readiness determines which endpoints receive ordinary traffic.')
    f.box(50,245,300,170,'External entry',['Browser / client','Ingress or Gateway controller','with a reachable entry point'],AMBER,18)
    f.box(450,245,280,170,'Service: web',['Stable DNS + virtual IP','port 80 -> targetPort 80','selector: app=web'],PURPLE,17)
    f.box(895,185,255,115,'Ready Pod A',['label: app=web'],GREEN)
    f.box(895,390,255,115,'Ready Pod B',['label: app=web'],GREEN)
    f.arrow([(350,330),(450,330)]); f.arrow([(730,330),(805,330),(805,240),(895,240)],GREEN)
    f.arrow([(805,330),(805,447),(895,447)],GREEN)
    f.box(50,555,1100,65,'Local debugging: kubectl port-forward -> one selected Pod',[],BLUE)
    f.footer('ClusterIP is internal. Port-forward is a temporary client process; it does not create a permanent public endpoint.')
    f.save()

    f = Figure('07-storage-lifecycle', 'A Pod asks for storage through a claim', 'PVC = request. PV = storage resource. StorageClass = provisioning policy.')
    f.box(50,185,300,145,'Pod',['Application mount: /data','References a claim by name'],GREEN)
    f.box(450,185,280,145,'PVC',['Example: 5 GiB, RWO','A namespace-scoped claim'],BLUE)
    f.box(850,185,300,145,'PV',['Cluster-scoped resource','Describes backing storage'],PURPLE)
    f.arrow([(350,260),(450,260)]); f.arrow([(730,260),(850,260)])
    f.text(365,225,'request',17,MUTED); f.text(775,225,'bind',17,MUTED)
    f.box(450,430,280,155,'StorageClass',['Policy + provisioner / CSI','Can allocate PV + volume'],AMBER,18)
    f.box(850,430,300,155,'Backing storage',['Local disk or cloud volume','The actual application bytes'],GREEN,18)
    f.arrow([(730,500),(850,500)],AMBER); f.arrow([(1000,430),(1000,330)],PURPLE)
    f.arrow([(200,330),(200,615),(1000,615),(1000,585)],GREEN)
    f.text(50,453,'Mounted volume I/O',18,GREEN,True)
    f.text(50,483,'PVC is not a data proxy.',18,MUTED)
    f.footer('Deleting a Pod, deleting a claim and deleting a local cluster have different effects. Persistence is not a backup.')
    f.save()

    f = Figure('08-minikube-two-stores', 'Our Minikube node runs inside host Docker', 'One local node combines control-plane and worker roles; its Pod runtime is containerd.')
    f.rect(50,180,1100,445,'white',BLUE)
    f.text(75,199,'UBUNTU HOST / DOCKER ENGINE',19,BLUE,True)
    f.box(75,275,350,155,'Host Docker image store',['dataeng-training:1.2.0','Building here does not automatically','populate the node image store.'],BLUE,18)
    f.rect(545,255,580,345,PALE[GREEN],GREEN)
    f.text(565,274,'MINIKUBE NODE CONTAINER: bigdata',21,GREEN,True)
    f.box(565,320,245,145,'Kubernetes',['Control plane + kubelet','Services and Pods'],GREEN,18)
    f.box(835,320,270,145,'containerd store',['Imported application image','Pod containers run here'],PURPLE,17)
    f.arrow([(425,385),(520,385),(520,485),(970,485),(970,465)],BLUE)
    f.text(430,345,'image import',17,BLUE)
    f.box(75,495,350,90,'Host source: ~/workspace',[],AMBER)
    f.box(565,510,540,65,'Node /course-workspace -> Pod /workspace',[],AMBER)
    f.arrow([(425,540),(565,540)],AMBER)
    f.footer('Deleting this profile removes node/PVC data. Host source files and the retained host Docker image remain separate.')
    f.save()

    f = Figure('09-cloud-options', 'The same Kubernetes ideas extend to managed clouds', 'Providers operate the control plane. You still define workloads, access, networking and data needs.')
    for x,title,product,color,lines in [
        (50,'AWS','Amazon EKS',AMBER,['Account + region + VPC','Compute: node capacity','Images: Amazon ECR','Storage: cloud CSI drivers','Access: AWS IAM']),
        (425,'Azure','Azure Kubernetes Service',BLUE,['Subscription + region + VNet','Compute: node pools','Images: Azure Container Registry','Storage: cloud CSI drivers','Access: Microsoft Entra ID']),
        (800,'Google Cloud','Google Kubernetes Engine',GREEN,['Project + region + VPC','Compute: managed node capacity','Images: Artifact Registry','Storage: cloud CSI drivers','Access: Google Cloud IAM'])]:
        f.box(x,185,350,420,title,[],color)
        f.text(x+18,249,product,22,color,True)
        for i,line in enumerate(lines):f.text(x+18,310+i*42,line,17)
    f.footer('Use a reachable cluster API and its kubeconfig context. Cloud image registries, disks and identities are provider-specific.')
    f.save()


if __name__ == '__main__':
    render()
    guide = (ROOT.parent / 'README.md').read_text(encoding='utf-8')
    guide = guide.replace('Open [the introduction notebook](00-kubernetes-introduction.ipynb) for the same illustrated lesson in Jupyter. ', '')
    parts = re.split(r'(?=^## )', guide, flags=re.M)
    cells = [{'cell_type': 'markdown', 'id': f'intro-{i:02d}', 'metadata': {},
              'source': part.strip().splitlines(keepends=True)} for i, part in enumerate(parts) if part.strip()]
    notebook = {'nbformat': 4, 'nbformat_minor': 5, 'metadata': {
        'kernelspec': {'display_name': 'Python 3', 'language': 'python', 'name': 'python3'},
        'language_info': {'name': 'python'}}, 'cells': cells}
    (ROOT.parent / '00-kubernetes-introduction.ipynb').write_text(json.dumps(notebook, indent=2)+'\n', encoding='utf-8')
    print('Generated 9 original SVG diagrams and 9 high-resolution PNG images.')
    print(f'Generated introduction notebook with {len(cells)} Markdown sections.')
