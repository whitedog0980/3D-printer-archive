"""Bambu Studio 프로젝트 3MF 작성기 (출력 설정 포함).

Bambu Studio 는 Metadata/project_settings.config 가 없는 3MF 를 열면 형상만 불러오고
설정은 버린다. 그래서 Bambu Studio 2.0.2 가 저장한 A1 프로젝트의 전체 설정
(bambu/a1_project_template.config, 출처: bambulab/BambuStudio
resources/calib/pressure_advance/auto_pa_line_single.3mf)을 틀로 삼아

  1. 필라멘트를 1개(Bambu PLA Basic @BBL A1)로 줄이고
  2. 공정 프리셋을 0.20mm Standard -> 0.16mm Optimal @BBL A1 로 바꾸고
  3. 이 스탠드용 설정(PROCESS_OVERRIDES)을 덮어쓴 뒤

Bambu 형식(3D/Objects/*.model + Metadata/model_settings.config)으로 저장한다.
부품별 설정(OBJECT_SETTINGS)은 model_settings.config 의 object 메타데이터로 들어간다.
"""
import json
import zipfile
from pathlib import Path

TEMPLATE = Path(__file__).resolve().parent / "bambu" / "a1_project_template.config"
APP_VERSION = "02.00.02.01"          # 틀과 같은 버전으로 기록

# 0.20mm Standard @BBL A1 -> 0.16mm Optimal @BBL A1 (fdm_process_single_0.16 기준 차이)
PROFILE_016 = {
    "layer_height": "0.16",
    "bottom_shell_layers": "4",
    "bottom_color_penetration_layers": "4",
    "top_shell_layers": "6",
    "top_color_penetration_layers": "6",
    "gap_infill_speed": ["300"],
    "internal_solid_infill_speed": ["300"],
    "sparse_infill_speed": ["330"],
    "overhang_1_4_speed": ["60"],
    "overhang_2_4_speed": ["30"],
    "overhang_3_4_speed": ["10"],
    "support_bottom_z_distance": "0.16",
    "support_top_z_distance": "0.16",
    "support_threshold_angle": "25",
}

# 이 스탠드용 공정 설정 (시스템 프리셋과 다른 값)
PROCESS_OVERRIDES = {
    # 강도
    "wall_loops": "4",
    "sparse_infill_density": "40%",
    "sparse_infill_pattern": "gyroid",
    "wall_generator": "arachne",
    # 안정성: 바깥 벽을 천천히 (나사산·작은 부품 품질)
    "outer_wall_speed": ["120"],
    # 서포트: 떼어내기 쉬운 트리 서포트, 바닥판에서만, 브리지는 지지 안 함
    "enable_support": "1",
    "support_type": "tree(auto)",
    "support_style": "tree_slim",
    "support_on_build_plate_only": "1",
    "bridge_no_support": "1",
    "support_object_xy_distance": "0.5",
    "support_interface_top_layers": "2",
    "support_interface_spacing": "0.5",
    # 브림 없음
    "brim_type": "no_brim",
    # 필라멘트 1개라 프라임 타워 불필요
    "enable_prime_tower": "0",
}

FINE = {"layer_height": "0.12", "sparse_infill_density": "100%",
        "support_top_z_distance": "0.12", "support_bottom_z_distance": "0.12"}

# 부품 이름(접두어) -> 부품별 설정
OBJECT_SETTINGS = {
    "head": FINE,
    "screw_RH": FINE,
    "screw_LH": FINE,
    "frame": FINE,
    "knob": {"sparse_infill_density": "100%"},
    # 차음 원통: 벽 2줄로만 출력
    "mic_sleeve": {"wall_loops": "2", "sparse_infill_density": "0%"},
}

FILAMENT = "Bambu PLA Basic @BBL A1"
FILAMENT_COLOUR = "#808080"


def project_settings():
    cfg = json.loads(TEMPLATE.read_text(encoding="utf-8"))
    n = len(cfg["filament_settings_id"])
    assert cfg["printer_settings_id"] == "Bambu Lab A1 0.4 nozzle"
    assert cfg["filament_settings_id"][0] == FILAMENT

    # 1. 필라멘트 1개로
    for key, val in list(cfg.items()):
        if isinstance(val, list) and len(val) == n:
            cfg[key] = val[:1]
    cfg["flush_volumes_matrix"] = ["0"]
    cfg["flush_volumes_vector"] = cfg["flush_volumes_vector"][:2]
    cfg["filament_colour"] = [FILAMENT_COLOUR]

    def put(target, settings):
        for key, val in settings.items():
            assert key in target, f"unknown setting {key}"
            cur = target[key]
            if isinstance(cur, list) and not isinstance(val, list):
                val = [val] * len(cur)
            target[key] = val

    # 2. 0.16mm Optimal -> 시스템 프리셋 값. 틀에서 바뀌어 있던 두 항목은 시스템 값으로 되돌려 비교
    put(cfg, PROFILE_016)
    system = dict(cfg, enable_prime_tower="1", wall_generator="classic")
    # 3. 스탠드 설정
    put(cfg, PROCESS_OVERRIDES)
    changed = sorted(k for k in PROCESS_OVERRIDES if cfg[k] != system[k])
    cfg["print_settings_id"] = "0.16mm Optimal @BBL A1"
    cfg["different_settings_to_system"] = [";".join(changed), "", ""]
    cfg["version"] = APP_VERSION
    return cfg


def object_settings(name):
    for prefix, s in OBJECT_SETTINGS.items():
        if name == prefix or name.startswith(prefix + "_"):
            return s
    return {}


NS = ('xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02" '
      'xmlns:BambuStudio="http://schemas.bambulab.com/package/2021" '
      'xmlns:p="http://schemas.microsoft.com/3dmanufacturing/production/2015/06" '
      'requiredextensions="p"')


def write(path, meshes, items, title):
    """meshes: {형상 이름: (verts, tris)}, items: [(오브젝트 이름, 형상 이름, x, y)]"""
    shape_ids = {name: i + 1 for i, name in enumerate(meshes)}
    first_obj = len(meshes) + 1

    sub = ['<?xml version="1.0" encoding="UTF-8"?>', f'<model unit="millimeter" xml:lang="en-US" {NS}>',
           ' <metadata name="BambuStudio:3mfVersion">1</metadata>', ' <resources>']
    for name, (v, t) in meshes.items():
        sid = shape_ids[name]
        sub.append(f'  <object id="{sid}" p:UUID="{sid:04x}0000-81cb-4c03-9d28-80fed5dfa1dc" type="model">')
        sub.append('   <mesh>\n    <vertices>')
        sub.extend(f'     <vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in v)
        sub.append('    </vertices>\n    <triangles>')
        sub.extend(f'     <triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in t)
        sub.append('    </triangles>\n   </mesh>\n  </object>')
    sub += [' </resources>', ' <build/>', '</model>']

    main = ['<?xml version="1.0" encoding="UTF-8"?>', f'<model unit="millimeter" xml:lang="en-US" {NS}>',
            f' <metadata name="Application">BambuStudio-{APP_VERSION}</metadata>',
            ' <metadata name="BambuStudio:3mfVersion">1</metadata>',
            f' <metadata name="Title">{title}</metadata>', ' <resources>']
    build = []
    cfg = ['<?xml version="1.0" encoding="UTF-8"?>', '<config>']
    plate = ['  <plate>', '    <metadata key="plater_id" value="1"/>',
             '    <metadata key="plater_name" value=""/>', '    <metadata key="locked" value="false"/>']
    for k, (obj_name, shape, x, y) in enumerate(items):
        oid = first_obj + k
        sid = shape_ids[shape]
        main.append(f'  <object id="{oid}" p:UUID="{k + 1:08x}-61cb-4c03-9d28-80fed5dfa1dc" type="model">')
        main.append(f'   <components>\n    <component p:path="/3D/Objects/object_1.model" objectid="{sid}" '
                    f'p:UUID="{k + 1:04x}0000-b206-40ff-9872-83e8017abed1" transform="1 0 0 0 1 0 0 0 1 0 0 0"/>')
        main.append('   </components>\n  </object>')
        build.append(f'  <item objectid="{oid}" p:UUID="{k + 1:08x}-b1ec-4553-aec9-835e5b724bb4" '
                     f'transform="1 0 0 0 1 0 0 0 1 {x:.4f} {y:.4f} 0" printable="1"/>')
        cfg.append(f'  <object id="{oid}">')
        cfg.append(f'    <metadata key="name" value="{obj_name}"/>')
        cfg.append('    <metadata key="extruder" value="1"/>')
        for key, val in object_settings(obj_name).items():
            cfg.append(f'    <metadata key="{key}" value="{val}"/>')
        cfg.append(f'    <part id="{sid}" subtype="normal_part">')
        cfg.append(f'      <metadata key="name" value="{obj_name}"/>')
        cfg.append('      <metadata key="matrix" value="1 0 0 0 0 1 0 0 0 0 1 0 0 0 0 1"/>')
        cfg.append('    </part>\n  </object>')
        plate += ['    <model_instance>', f'      <metadata key="object_id" value="{oid}"/>',
                  '      <metadata key="instance_id" value="0"/>',
                  f'      <metadata key="identify_id" value="{100 + k}"/>', '    </model_instance>']
    main += [' </resources>', ' <build p:UUID="2c7c17d8-22b5-4d84-8835-1976022ea369">', *build, ' </build>', '</model>']
    cfg += plate + ['  </plate>', '</config>']

    rel = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">\n'
           ' <Relationship Target="{}" Id="rel-1" '
           'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>\n</Relationships>')
    with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
        z.writestr("[Content_Types].xml",
                   '<?xml version="1.0" encoding="UTF-8"?>\n'
                   '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\n'
                   ' <Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>\n'
                   ' <Default Extension="model" ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>\n'
                   ' <Default Extension="png" ContentType="image/png"/>\n'
                   ' <Default Extension="gcode" ContentType="text/x.gcode"/>\n</Types>')
        z.writestr("_rels/.rels", rel.format("/3D/3dmodel.model"))
        z.writestr("3D/3dmodel.model", "\n".join(main))
        z.writestr("3D/_rels/3dmodel.model.rels", rel.format("/3D/Objects/object_1.model"))
        z.writestr("3D/Objects/object_1.model", "\n".join(sub))
        z.writestr("Metadata/project_settings.config",
                   json.dumps(project_settings(), indent=4, ensure_ascii=False))
        z.writestr("Metadata/model_settings.config", "\n".join(cfg))
        z.writestr("Metadata/slice_info.config",
                   '<?xml version="1.0" encoding="UTF-8"?>\n<config>\n  <header>\n'
                   '    <header_item key="X-BBL-Client-Type" value="slicer"/>\n'
                   f'    <header_item key="X-BBL-Client-Version" value="{APP_VERSION}"/>\n'
                   '  </header>\n</config>')
