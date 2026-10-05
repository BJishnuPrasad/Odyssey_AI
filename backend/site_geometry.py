"""Architecturally informed procedural illustrations, never survey-derived meshes."""
import math


def build_site(s):
    parts=[]
    stone='#b59a76'; dark='#675441'; trim='#d3b88c'; plaster='#e2d2ac'
    def part(shape,pos,size,color=stone,**kwargs):
        parts.append({'shape':shape,'position':pos,'size':size,'color':color,**kwargs})
    def box(x,y,z,w,h,d,color=stone,**kwargs): part('box',[x,y+h/2,z],[w,h,d],color,**kwargs)
    def cylinder(x,y,z,rt,rb,h,n=24,color=stone,**kwargs): part('cylinder',[x,y+h/2,z],[rt,rb,h,n],color,**kwargs)
    def sphere(x,y,z,r,color=stone,**kwargs): part('sphere',[x,y,z],[r],color,**kwargs)
    def column(x,y,z,h,r=.48,color=stone):
        box(x,y,z,r*2.8,.35,r*2.8,color)
        cylinder(x,y+.35,z,r*.74,r,h-.85,8,color)
        box(x,y+h-.5,z,r*3.3,.5,r*3.3,trim)
    def stairs(x,y,z,w,count,rise=.25,run=.65):
        for j in range(count): box(x,y,z+j*run,w,rise*(count-j),run,trim)
    def hall(x,z,w,d,h,y=0):
        box(x,y,z,w+2,1.2,d+2,dark)
        # Raised mandapa, open colonnades, heavy cornice and flat slab roof.
        for xx in (-w/2,w/2):
            for i in range(max(3,int(d/3.4))): column(x+xx,y+1.2,z-d/2+1.2+i*(d-2.4)/max(2,int(d/3.4)-1),h-2)
        for zz in (-d/2,d/2):
            for i in range(1,4): column(x-w/2+i*w/4,y+1.2,z+zz,h-2)
        box(x,y+h-.8,z,w+3,.6,d+3,trim)
        box(x,y+h-.2,z,w+1,1,d+1)
        box(x,y+h+.8,z,w,.25,d,trim)
    def vimana(x,z,h,base=25,tiers=13):
        box(x,0,z,base+6,1.4,base+6,dark)
        box(x,1.4,z,base+3,1.1,base+3,trim)
        base_h=h*.16; box(x,2.5,z,base,base_h,base)
        box(x,2.5,z+base/2+.05,base*.16,base_h*.7,.3,dark)
        for side in (-1,1):
            for j in (-.34,-.17,.17,.34):
                box(x+j*base,2.7,z+side*base/2,.6,base_h-.2,.5,trim)
                box(x+side*base/2,2.7,z+j*base,.5,base_h-.2,.6,trim)
        y=2.5+base_h; level_h=(h*.70-2.5)/tiers
        for i in range(tiers):
            w=base*(1-.70*i/tiers); nextw=base*(1-.70*(i+1)/tiers)
            # Four-sided tapered stone core, oriented to the building axes.
            cylinder(x,y,z,nextw/math.sqrt(2),w/math.sqrt(2),level_h,4,stone,rotation=[0,math.pi/4,0])
            box(x,y,z,w+1.2,.4,w+1.2,trim)
            # Repeated shallow niches/miniature pavilions suggest architectural rhythm.
            for side in (-1,1):
                for j in (-.30,0,.30):
                    box(x+j*w,y+.45,z+side*w*.47,.8,level_h*.5,.35,dark,shadow=False)
                    box(x+side*w*.47,y+.45,z+j*w,.35,level_h*.5,.8,dark,shadow=False)
            y+=level_h
        cylinder(x,y,z,base*.17,base*.20,h*.055,8,trim)
        sphere(x,y+h*.095,z,base*.20,stone,scale=[1,.68,1])
        cylinder(x,y+h*.10,z,.3,.75,h*.045,12,'#a98a3c')
        sphere(x,y+h*.15,z,.5,'#bd9c47')
    def gateway(z,w=15,h=18):
        for x in (-w*.34,w*.34): box(x,0,z,w*.32,h*.30,5)
        box(0,h*.30,z,w,1.2,5.8,trim)
        for i in range(6): box(0,h*.30+1.2+i*h*.09,z,w*(1-i*.095),h*.085,5*(1-i*.085))
        cylinder(0,h*.96,z,1.1,1.1,w*.55,16,trim,rotation=[0,0,math.pi/2])
    def compound(w,d):
        for x in (-w/2,w/2): box(x,0,0,1.2,3.2,d,stone)
        box(0,0,-d/2,w,3.2,1.2)
        for x in (-w*.30,w*.30): box(x,0,d/2,w*.4,3.2,1.2)
        for x in (-w/2,w/2):
            for z in (-d/2,d/2): cylinder(x,0,z,2.2,2.2,4,8)
    typology=s['typology']; identity=s['id']
    if typology=='temple':
        big=identity=='relation-6668806'
        height=s.get('height_m') or (64.8 if big else 24)
        box(0,-1,5,94,1,150,'#777a61',material='ground')
        box(0,-.1,5,79,.18,138,'#b8ae98',material='paving')
        compound(80,138)
        vimana(0,-24,height,26 if big else 20,13 if big else 7)
        hall(0,7,18,35,9 if big else 6)
        stairs(0,0,25.5,12,5)
        hall(0,44,12,12,7)
        # A low, abstract Nandi silhouette remains explicitly illustrative.
        sphere(0,3.1,44,2.2,dark,scale=[.65,.55,1.35])
        sphere(0,4,45.8,1.1,dark,scale=[.75,1,.8])
        gateway(66,16,21 if big else 15)
        for x in (-31,31):
            for z in (-43,-17,10,37):
                hall(x,z,8,10,4)
        if not big:
            # Darasuram's chariot-form mandapa is indicated by stone wheels.
            for x in (-10,10):
                for z in (4,15): cylinder(x,1.5,z,1.7,1.7,.65,24,dark,rotation=[0,0,math.pi/2])
    elif typology=='fort':
        box(0,-1,0,68,1,68,'#7f8564',material='ground')
        cylinder(0,-.1,0,27,27,.25,64,'#527f7b',material='water')
        cylinder(0,0,0,21,21,1.1,6,dark)
        for i in range(8):
            y=1.1+i*2.6; radius=7.8-i*.45
            cylinder(0,y,0,radius-.25,radius,2.6,6,plaster)
            cylinder(0,y+2.25,0,radius+.6,radius+.6,.35,6,trim)
            for face in range(6):
                angle=face*math.pi/3; x,z=math.sin(angle)*radius*.88,math.cos(angle)*radius*.88
                box(x,y+.35,z,1.3,1.55,.20,dark,rotation=[0,angle,0])
                sphere(x,y+1.9,z,.65,dark,scale=[1,.55,.12],rotation=[0,angle,0])
        cylinder(0,21.9,0,2.6,4.2,1,6,plaster); sphere(0,23.2,0,2.3,trim,scale=[1,.45,1])
        cylinder(0,24,0,.08,.08,3,8,dark)
        for i in range(6):
            a=i*math.pi/3; box(math.sin(a)*18,1,math.cos(a)*18,16,2,2,plaster,rotation=[0,a,0])
    elif typology=='palace':
        box(0,-1,0,90,1,80,'#818363',material='ground')
        for x,z,w,d in [(0,-25,68,12),(-29,0,12,44),(29,0,12,44),(0,24,68,12)]:
            box(x,0,z,w,9,d,plaster); box(x,9,z,w+1,.7,d+1,trim)
            for j in range(max(2,int(w/5))):
                xx=x-w/2+2.5+j*5; box(xx,2,z+d/2+.06,2.1,3.8,.2,dark)
                sphere(xx,5.8,z+d/2+.1,1.05,dark,scale=[1,.5,.15])
        hall(0,-10,27,12,9)
        for i in range(7):
            w=15-i*1.1; box(21,9+i*3.4,-20,w,3.4,w,plaster); box(21,12.0+i*3.4,-20,w+1,.4,w+1,trim)
            box(21,9.7+i*3.4,-20+w/2+.05,2,1.8,.2,dark)
        sphere(-22,12,-20,7,trim,scale=[1,.65,1]); cylinder(-22,15,-20,.25,.6,2,12,'#9a7b35')
    elif typology=='dam':
        box(0,-1,0,110,1,70,'#768363',material='ground')
        box(0,-.1,0,110,.25,52,'#477e85',material='water')
        box(0,0,0,98,4,8,'#9d9885')
        box(0,4,0,100,.6,9,trim)
        for x in range(-45,46,5):
            box(x,0,4.8,1.2,4.2,2,stone)
            box(x,4.6,-3.5,.6,1.2,.6,plaster)
        box(0,5.5,-3.5,98,.35,.5,plaster)
        for z in (-16,-10,12,17,23): box(0,.18,z,102,.04,.12,'#8cbbb9',material='water',shadow=False)
    elif typology=='tower':
        box(0,-.7,0,36,.7,26,'#aba58c',material='paving'); gateway(0,20,25)
        stairs(0,0,3,8,5)
    else:
        box(0,-.6,0,34,.6,30,'#7f8668',material='ground')
        hall(0,0,14,14,8)
        stairs(0,0,8,8,5)
        box(0,1.2,0,3,1,3,dark)
        cylinder(0,2.2,0,.7,.9,2.4,16,dark)
        sphere(0,5.1,0,.7,dark)
        if typology=='shrine':
            box(0,9.2,0,.35,3,.35,plaster); box(0,10.9,0,2,.35,.35,plaster)
    return {'parts':parts,'height_m':s.get('height_m'),'height_basis':s.get('height_basis','Architectural proportions estimated; no surveyed dimensions'),
            'units':'Architecturally informed reconstruction; decorative details and layout are illustrative',
            'features':['Pillared halls and cornices','Site-specific massing','Procedural stone/paving materials','Sunlight and cast shadows']}
