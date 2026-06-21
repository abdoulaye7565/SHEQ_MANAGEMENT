lines = open('mobile_app.py', encoding='utf-8').readlines()

# Find _s_home start and _s_maint start
start_line = next(i for i,l in enumerate(lines) if '    def _s_home():' in l)
end_line   = next(i for i,l in enumerate(lines) if '    def _s_maint():' in l)
print(f'Replacing lines {start_line+1}..{end_line} with new _s_home')

new_home = r'''    def _s_home():
        MO=["Janv","Févr","Mars","Avr","Mai","Juin","Juil","Août","Sep","Oct","Nov","Déc"]
        JO=["Lundi","Mardi","Mercredi","Jeudi","Vendredi","Samedi","Dimanche"]
        d=date.today()
        date_long=f"{JO[d.weekday()]} {d.day} {MO[d.month-1]} {d.year}"
        dash=cj("dashboard"); site=dash.get("site") or "SYAMA"
        uname=get_setting("identity_username") or ""
        display_name=uname if uname and uname not in ("—","") else "Agent"
        urole=get_setting("profile_label") or "Agent HSE"
        inits="".join(w[0].upper() for w in display_name.split() if w)[:2] or "AG"
        tot=total_pending(); online=bool(get_setting("mobile_session"))

        # ── Sidebar drawer ────────────────────────────────────────────────────
        DRW={"open":False}
        drw_bg   =ft.Container(expand=True,bgcolor="#00000060",visible=False,ink=True)
        drw_panel=ft.Container(visible=False,bgcolor=NAV,width=275,shadow=SH(32,"55"))

        def open_drawer(e=None):
            DRW["open"]=True; drw_bg.visible=True; drw_panel.visible=True
            try: drw_bg.update(); drw_panel.update()
            except Exception: pass
        def close_drawer(e=None):
            DRW["open"]=False; drw_bg.visible=False; drw_panel.visible=False
            try: drw_bg.update(); drw_panel.update()
            except Exception: pass
        drw_bg.on_click=close_drawer

        def _nav_grp(label):
            return ft.Container(padding=P(16,12,16,6),
                content=ft.Text(label,size=9,weight=ft.FontWeight.W_700,
                                color="#3D6B99"))
        def _nav_item(label,icon,color,key):
            def click(e,k=key): close_drawer(); go_to(k)
            return ft.Container(border_radius=10,margin=ft.margin.symmetric(horizontal=8,vertical=1),
                ink=True,on_click=click,padding=P(10,10,10,10),
                content=ft.Row([
                    ft.Container(bgcolor=f"{color}20",border_radius=8,width=32,height=32,
                        alignment=AL(0,0),content=ft.Icon(icon,color=color,size=16)),
                    ft.Text(label,size=13,weight=ft.FontWeight.W_500,color="#CBD5E1"),
                ],spacing=10))

        drw_panel.content=ft.Column([
            ft.Container(gradient=GRAD,padding=P(20,28,20,18),
                content=ft.Column([
                    ft.Row([
                        ft.Container(bgcolor="#FFFFFF20",border_radius=28,padding=ft.padding.all(2),
                            content=_ava(inits,48)),
                        ft.Container(width=12),
                        ft.Column([
                            ft.Text(display_name,size=15,weight=ft.FontWeight.BOLD,color="#FFFFFF",
                                    max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                            ft.Text(urole,size=11,color="#93C5FD"),
                            ft.Row([ft.Icon(ft.Icons.LOCATION_ON_ROUNDED,color="#60A5FA",size=11),
                                    ft.Text(site,size=10,color="#60A5FA")],spacing=3),
                        ],spacing=3,expand=True),
                    ],spacing=0),
                    ft.Container(height=8),
                    ft.Container(bgcolor="#FFFFFF12",border_radius=10,padding=P(10,6,10,6),
                        content=ft.Row([
                            ft.Container(width=8,height=8,bgcolor=OK if online else DNG,border_radius=4),
                            ft.Text(f"{'Connecté' if online else 'Hors-ligne'} · {tot} en attente",
                                    size=11,color="#93C5FD",expand=True),
                        ],spacing=8)),
                ],spacing=0,tight=True)),
            ft.Container(expand=True,
                content=ft.Column([
                    _nav_grp("TABLEAU DE BORD"),
                    _nav_item("Accueil",ft.Icons.HOME_ROUNDED,"#60A5FA","home"),
                    _nav_grp("MAINTENANCE"),
                    _nav_item("Interventions",ft.Icons.BUILD_ROUNDED,BLUE,"intervention"),
                    _nav_item("Inspections",ft.Icons.FACT_CHECK_ROUNDED,INFO,"inspection"),
                    _nav_item("Équipements",ft.Icons.HANDYMAN_OUTLINED,BLUE,"maintenance"),
                    _nav_grp("SÉCURITÉ"),
                    _nav_item("Pointage terrain",ft.Icons.HOW_TO_REG_ROUNDED,OK,"attendance"),
                    _nav_item("Vérification EPI",ft.Icons.SAFETY_CHECK_OUTLINED,WARN,"ppe_check"),
                    _nav_item("Dotation EPI",ft.Icons.ASSIGNMENT_TURNED_IN_ROUNDED,OK,"ppe_assign"),
                    _nav_item("Incidents",ft.Icons.WARNING_ROUNDED,DNG,"incident"),
                    _nav_item("Alertes",ft.Icons.NOTIFICATIONS_ACTIVE_OUTLINED,DNG,"alerts"),
                    _nav_grp("FORMATION"),
                    _nav_item("Toolbox Talk",ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP,"toolbox"),
                    _nav_grp("DOCUMENTS"),
                    _nav_item("Timesheets & Exports",ft.Icons.ARTICLE_OUTLINED,BLUE,"timesheet"),
                    _nav_grp("COMPTE"),
                    _nav_item("Mon profil",ft.Icons.MANAGE_ACCOUNTS_OUTLINED,INFO,"profile"),
                    _nav_item("Paramètres",ft.Icons.SETTINGS_OUTLINED,MUT,"settings"),
                ],spacing=0,scroll=ft.ScrollMode.AUTO)),
            ft.Container(padding=P(16,8,16,12),
                content=ft.Text("OREZONE QHSE Mobile · v2.0",size=10,color="#2D4A6F",
                                text_align=ft.TextAlign.CENTER)),
        ],spacing=0,expand=True)

        # ── Dashboard KPI data ────────────────────────────────────────────────
        dsh=cj("dashboard")
        eq  =str(dsh.get("equipment_active") or "—")
        iv  =str(dsh.get("interventions_open") or "—")
        rt  =str(dsh.get("en_retard") or "—")
        al  =str(dsh.get("alertes_ouvertes") or "—")

        # ── KPI card ──────────────────────────────────────────────────────────
        def _kpi(val,lbl,color,icon,on_click=None):
            return ft.Container(expand=True,bgcolor=CARD,border_radius=18,
                shadow=SH(6,"10"),border=ft.border.all(1,f"{color}18"),
                ink=bool(on_click),on_click=on_click,
                padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Row([
                        ft.Container(bgcolor=f"{color}18",border_radius=12,width=36,height=36,
                            alignment=AL(0,0),
                            content=ft.Icon(icon,color=color,size=18)),
                        ft.Container(expand=True),
                        ft.Container(width=8,height=8,bgcolor=color,border_radius=4,
                            opacity=0.7),
                    ],spacing=4),
                    ft.Container(height=8),
                    ft.Text(val,size=28,weight=ft.FontWeight.BOLD,color=color),
                    ft.Text(lbl,size=10,color=MUT,weight=ft.FontWeight.W_500),
                ],spacing=0,tight=True))

        # ── Module tile (2-col grid) ───────────────────────────────────────────
        def _mod(label,sub,icon,color,key):
            def click(e): go_to(key)
            return ft.Container(expand=True,bgcolor=CARD,border_radius=16,
                shadow=SH(4,"08"),border=ft.border.all(1,f"{color}18"),
                ink=True,on_click=click,padding=P(14,12,14,12),
                content=ft.Column([
                    ft.Container(bgcolor=f"{color}15",border_radius=12,width=44,height=44,
                        alignment=AL(0,0),
                        content=ft.Icon(icon,color=color,size=22)),
                    ft.Container(height=8),
                    ft.Text(label,size=13,weight=ft.FontWeight.W_700,color=TXT,
                            max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                    ft.Text(sub,size=10,color=MUT,max_lines=2,
                            overflow=ft.TextOverflow.ELLIPSIS),
                ],spacing=2,tight=True))

        # ── Alert card ─────────────────────────────────────────────────────────
        def _ac_alert(a):
            niv=str(a.get("niveau","") or "").lower()
            c=DNG if niv in ("critique","haut") else WARN if niv=="moyen" else INFO
            return ft.Container(bgcolor=CARD,border_radius=14,
                border=ft.border.all(1,f"{c}25"),padding=P(12,10,12,10),
                content=ft.Row([
                    ft.Container(width=4,height=36,bgcolor=c,border_radius=3),
                    ft.Container(width=10),
                    ft.Column([
                        ft.Text(str(a.get("titre","Alerte") or "Alerte"),size=12,
                                weight=ft.FontWeight.W_600,color=TXT,
                                max_lines=1,overflow=ft.TextOverflow.ELLIPSIS),
                        ft.Text(str(a.get("description","") or "")[:60],
                                size=10,color=MUT,max_lines=1,
                                overflow=ft.TextOverflow.ELLIPSIS),
                    ],spacing=2,expand=True),
                    ft.Container(bgcolor=f"{c}15",border_radius=8,padding=P(6,3,6,3),
                        content=ft.Text(niv.upper() or "?",size=9,color=c,
                                        weight=ft.FontWeight.W_700)),
                ],spacing=0))

        all_a=cj("alerts",[]);
        if not isinstance(all_a,list): all_a=[]
        crit=[a for a in all_a if a.get("niveau") in {"critique","haut"}][:3]

        main_content=ft.Column([
            # ── HEADER ────────────────────────────────────────────────────────
            ft.Container(gradient=GRAD,padding=P(16,18,16,20),shadow=SH(14,"25"),
                content=ft.Column([
                    ft.Row([
                        ft.Container(width=38,height=38,border_radius=12,bgcolor="#FFFFFF18",
                            alignment=AL(0,0),ink=True,on_click=open_drawer,
                            content=ft.Icon(ft.Icons.MENU_ROUNDED,color="#FFFFFF",size=21)),
                        ft.Container(width=8),
                        ft.Column([
                            ft.Text("OREZONE QHSE",size=15,weight=ft.FontWeight.W_800,
                                    color="#FFFFFF"),
                            ft.Text("SYAMA Mining",size=10,color="#93C5FD"),
                        ],spacing=0,expand=True),
                        # Status dot
                        ft.Container(bgcolor="#FFFFFF18",border_radius=20,
                            padding=P(8,6,8,6),
                            content=ft.Row([
                                ft.Container(width=6,height=6,bgcolor=OK if online else DNG,
                                    border_radius=3),
                                ft.Text("Online" if online else "Offline",
                                        size=10,color="#FFFFFF",weight=ft.FontWeight.W_600),
                            ],spacing=5,tight=True)),
                        ft.Container(width=6),
                        ft.Container(width=36,height=36,border_radius=18,bgcolor="#FFFFFF1A",
                            alignment=AL(0,0),ink=True,on_click=lambda e:go_to("alerts"),
                            content=ft.Icon(ft.Icons.NOTIFICATIONS_OUTLINED,color="#FFFFFF",size=18)),
                        ft.Container(width=6),
                        ft.Container(ink=True,border_radius=20,on_click=lambda e:go_to("profile"),
                            content=_ava(inits,36)),
                    ],spacing=4),
                    ft.Container(height=14),
                    # User greeting block
                    ft.Container(bgcolor="#FFFFFF10",border_radius=16,padding=P(14,12,14,12),
                        content=ft.Row([
                            ft.Column([
                                ft.Text(f"Bonjour, {display_name} 👋",size=18,
                                        weight=ft.FontWeight.BOLD,color="#FFFFFF"),
                                ft.Container(height=4),
                                ft.Row([
                                    ft.Icon(ft.Icons.CALENDAR_TODAY_ROUNDED,color="#93C5FD",size=12),
                                    ft.Text(date_long,size=11,color="#93C5FD"),
                                ],spacing=5),
                                ft.Row([
                                    ft.Icon(ft.Icons.LOCATION_ON_ROUNDED,color="#60A5FA",size=12),
                                    ft.Text(f"{site} · {urole}",size=11,color="#60A5FA"),
                                ],spacing=5),
                            ],spacing=3,expand=True),
                            ft.Container(
                                bgcolor="#FFFFFF18",border_radius=14,
                                padding=P(10,10,10,10),
                                content=ft.Column([
                                    ft.Text(str(d.day),size=24,weight=ft.FontWeight.BOLD,
                                            color="#FFFFFF",text_align=ft.TextAlign.CENTER),
                                    ft.Text(MO[d.month-1].upper(),size=9,color="#93C5FD",
                                            text_align=ft.TextAlign.CENTER,
                                            weight=ft.FontWeight.W_700),
                                    ft.Text(str(d.year),size=9,color="#7AADDE",
                                            text_align=ft.TextAlign.CENTER),
                                ],spacing=1,horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                                tight=True)),
                        ],spacing=12)),
                    # Sync banner (inside header)
                    ft.Container(visible=tot>0,height=0 if tot==0 else None,
                        margin=ft.margin.only(top=8),
                        content=ft.Container(bgcolor="#FFFBEB",border_radius=10,
                            padding=P(10,7,10,7),
                            content=ft.Row([
                                ft.Icon(ft.Icons.CLOUD_UPLOAD_ROUNDED,color=WARN,size=15),
                                ft.Text(f"{tot} élément(s) en attente de synchronisation",
                                        size=11,color="#92400E",expand=True),
                                ft.Container(bgcolor=WARN,border_radius=8,padding=P(8,4,8,4),
                                    ink=True,on_click=do_sync,
                                    content=ft.Text("Sync",size=10,color="#FFFFFF",
                                                    weight=ft.FontWeight.W_700)),
                            ],spacing=8))),
                ],spacing=0,tight=True)),

            # ── BODY ──────────────────────────────────────────────────────────
            ft.Container(expand=True,padding=P(12,14,12,0),
                content=ft.Column([
                    # KPI row (4 cards horizontal)
                    ft.Row([
                        _kpi(eq,"Équipements",BLUE,ft.Icons.HANDYMAN_ROUNDED,
                             lambda e:go_to("maintenance")),
                        _kpi(iv,"Interventions",WARN,ft.Icons.BUILD_CIRCLE_OUTLINED,
                             lambda e:go_to("intervention")),
                        _kpi(rt,"En retard",DNG,ft.Icons.WARNING_AMBER_ROUNDED,
                             lambda e:go_to("maintenance")),
                        _kpi(al,"Alertes",INFO,ft.Icons.NOTIFICATIONS_ACTIVE_ROUNDED,
                             lambda e:go_to("alerts")),
                    ],spacing=10),

                    # Toolbox banner (if topic for today)
                    h_tb,

                    # ── MODULES GRID ─────────────────────────────────────────
                    ft.Container(bgcolor=CARD,border_radius=16,shadow=SH(4,"08"),
                        border=ft.border.all(1,BRD),padding=P(14,12,14,14),
                        content=ft.Column([
                            ft.Row([
                                ft.Icon(ft.Icons.GRID_VIEW_ROUNDED,color=BLUE,size=14),
                                ft.Text("Modules",size=12,weight=ft.FontWeight.W_700,
                                        color=BLUE,expand=True),
                                ft.Container(bgcolor=f"{BLUE}10",border_radius=8,
                                    padding=P(6,3,6,3),ink=True,
                                    on_click=lambda e:go_to("attendance"),
                                    content=ft.Text("Tout voir",size=10,color=BLUE,
                                                    weight=ft.FontWeight.W_600)),
                            ],spacing=8),
                            ft.Container(height=10),
                            ft.Row([
                                _mod("Pointage","Présence terrain",
                                     ft.Icons.HOW_TO_REG_ROUNDED,OK,"attendance"),
                                ft.Container(width=10),
                                _mod("Intervention","Maintenance corrective",
                                     ft.Icons.BUILD_ROUNDED,BLUE,"intervention"),
                            ],spacing=0),
                            ft.Container(height=10),
                            ft.Row([
                                _mod("EPI","Vérification & dotation",
                                     ft.Icons.SAFETY_CHECK_ROUNDED,WARN,"ppe_check"),
                                ft.Container(width=10),
                                _mod("Toolbox","Causerie sécurité",
                                     ft.Icons.RECORD_VOICE_OVER_ROUNDED,PURP,"toolbox"),
                            ],spacing=0),
                            ft.Container(height=10),
                            ft.Row([
                                _mod("Incident","Déclarer un événement",
                                     ft.Icons.WARNING_ROUNDED,DNG,"incident"),
                                ft.Container(width=10),
                                _mod("Timesheets","Télécharger & exporter",
                                     ft.Icons.ARTICLE_OUTLINED,INFO,"timesheet"),
                            ],spacing=0),
                        ],spacing=0,tight=True)),

                    # ── ALERTES CRITIQUES ─────────────────────────────────────
                    ft.Row([
                        ft.Icon(ft.Icons.PRIORITY_HIGH_ROUNDED,color=DNG,size=14),
                        ft.Text("Alertes critiques",size=12,weight=ft.FontWeight.W_700,
                                color=DNG,expand=True),
                        ft.Container(bgcolor=f"{DNG}10",border_radius=8,padding=P(6,3,6,3),
                            ink=True,on_click=lambda e:go_to("alerts"),
                            content=ft.Text("Voir tout",size=10,color=DNG,
                                            weight=ft.FontWeight.W_600)),
                    ],spacing=8),
                    *(
                        [_ac_alert(a) for a in crit] or [
                            ft.Container(bgcolor=f"{OK}08",border_radius=14,
                                border=ft.border.all(1,f"{OK}25"),padding=P(14,12,14,12),
                                content=ft.Row([
                                    ft.Container(bgcolor=f"{OK}18",border_radius=10,
                                        width=36,height=36,alignment=AL(0,0),
                                        content=ft.Icon(ft.Icons.CHECK_CIRCLE_OUTLINE_ROUNDED,
                                                        color=OK,size=20)),
                                    ft.Column([
                                        ft.Text("Aucune alerte critique",size=13,
                                                weight=ft.FontWeight.W_600,color=OK),
                                        ft.Text("Situation sous contrôle",size=11,color=MUT),
                                    ],spacing=2,expand=True),
                                ],spacing=10))
                        ]
                    ),
                    ft.Container(height=80),
                ],spacing=12,scroll=ft.ScrollMode.AUTO,expand=True)),
        ],spacing=0,expand=True)

        return ft.Container(bgcolor=BG,expand=True,
            content=ft.Stack([
                main_content,
                drw_bg,
                drw_panel,
            ]))

'''

new_lines = lines[:start_line] + [new_home] + lines[end_line:]
with open('mobile_app.py', 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
print(f'Done. Total lines: {len(new_lines)}')
