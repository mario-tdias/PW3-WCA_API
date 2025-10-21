from flask import render_template, request
import urllib
import urllib.parse
import json


def init_app(app):
    def _famous_competitors():
        names = [
            'Yiheng Wang',
            'Max Park',
            'Tymon Kolasinski',
            'Sebastian Weyer',
            'Mats Valk',
            'Patrick Ponce',
            'Lucas Etter',
            'Stanley Chapel',
            'Leo Borromeo',
            'Ruihang Xu'
        ]
        items = []
        for name in names:
            try:
                encoded_q = urllib.parse.quote(name)
                wca_url = f"https://www.worldcubeassociation.org/api/v0/search/users?q={encoded_q}"
                response = urllib.request.urlopen(wca_url)
                data = response.read()
                json_data = json.loads(data)
                results = json_data.get('result') or json_data.get('results') or []
                item = next((it for it in results if isinstance(it, dict) and (it.get('class') == 'user' or it.get('wca_id'))), None)
                if not item:
                    continue
                avatar_obj = item.get('avatar') or {}
                avatar_url = avatar_obj.get('url') if isinstance(avatar_obj, dict) else None
                avatar_thumb_url = avatar_obj.get('thumb_url') if isinstance(avatar_obj, dict) else None
                profile_url = None
                if item.get('wca_id'):
                    profile_url = f"https://www.worldcubeassociation.org/persons/{item.get('wca_id')}"
                elif item.get('url'):
                    raw_url = item.get('url')
                    profile_url = raw_url if raw_url.startswith('http') else f"https://www.worldcubeassociation.org{raw_url}"
                items.append({
                    'name': item.get('name'),
                    'wca_id': item.get('wca_id'),
                    'country_iso2': item.get('country_iso2'),
                    'avatar_url': avatar_url,
                    'avatar_thumb_url': avatar_thumb_url,
                    'profile_url': profile_url,
                    'competition_count': None,
                    'medals_gold': None,
                    'medals_silver': None,
                    'medals_bronze': None,
                    'medals_total': None
                })
            except Exception:
                continue
        # Enriquecer com medalhas/contagem de competições e recordes
        def _extract_competition_count(payload):
            if not isinstance(payload, dict):
                return None
            for key in ['competition_count', 'competitions_count', 'num_competitions']:
                num = payload.get(key)
                try:
                    num = int(num)
                except Exception:
                    num = None
                if isinstance(num, int) and num >= 0:
                    return num
            person = payload.get('person')
            if isinstance(person, dict):
                for key in ['competition_count', 'competitions_count', 'num_competitions']:
                    try:
                        num = int(person.get(key))
                    except Exception:
                        num = None
                    if isinstance(num, int) and num >= 0:
                        return num
            for list_key in ['competitions', 'participations', 'competition_participations']:
                lst = payload.get(list_key)
                if isinstance(lst, list):
                    return len(lst)
            return None
        def _accumulate_record_counts(payload):
            counts = {'wr': 0, 'cr': 0, 'nr': 0}
            if not isinstance(payload, dict):
                return counts
            records = payload.get('records') or payload.get('current_records') or payload.get('record')
            def walk(node):
                if isinstance(node, dict):
                    for k, v in node.items():
                        key = str(k).lower()
                        if key in ['world', 'wr']:
                            try:
                                if isinstance(v, (int, float)) and int(v) > 0: counts['wr'] += int(v)
                                elif isinstance(v, (str, bytes)) and v: counts['wr'] += 1
                                elif isinstance(v, bool) and v: counts['wr'] += 1
                                elif isinstance(v, dict) or isinstance(v, list):
                                    before = counts['wr']; walk(v); counts['wr'] += 0 if counts['wr'] == before else 0
                            except Exception:
                                pass
                        if key in ['continental', 'continent', 'cr']:
                            try:
                                if isinstance(v, (int, float)) and int(v) > 0: counts['cr'] += int(v)
                                elif isinstance(v, (str, bytes)) and v: counts['cr'] += 1
                                elif isinstance(v, bool) and v: counts['cr'] += 1
                                elif isinstance(v, dict) or isinstance(v, list):
                                    before = counts['cr']; walk(v); counts['cr'] += 0 if counts['cr'] == before else 0
                            except Exception:
                                pass
                        if key in ['national', 'country', 'nr']:
                            try:
                                if isinstance(v, (int, float)) and int(v) > 0: counts['nr'] += int(v)
                                elif isinstance(v, (str, bytes)) and v: counts['nr'] += 1
                                elif isinstance(v, bool) and v: counts['nr'] += 1
                                elif isinstance(v, dict) or isinstance(v, list):
                                    before = counts['nr']; walk(v); counts['nr'] += 0 if counts['nr'] == before else 0
                            except Exception:
                                pass
                        walk(v)
                elif isinstance(node, list):
                    for it in node:
                        walk(it)
            if isinstance(records, (dict, list)):
                walk(records)
            else:
                walk(payload)
            return counts
        for comp in items:
            wca_id = comp.get('wca_id')
            if not wca_id:
                continue
            totals = {'gold': 0, 'silver': 0, 'bronze': 0}
            found = False
            comp_count = None
            rec_counts = {'wr': 0, 'cr': 0, 'nr': 0}
            # 1) Fonte oficial persons/{id}.json
            try:
                official_url = f"https://www.worldcubeassociation.org/persons/{wca_id}.json"
                req = urllib.request.Request(official_url, headers={
                    'User-Agent': 'Mozilla/5.0',
                    'Accept': 'application/json'
                })
                resp = urllib.request.urlopen(req, timeout=10)
                payload = json.loads(resp.read())
                if comp_count is None:
                    comp_count = _extract_competition_count(payload)
                try:
                    rc = _accumulate_record_counts(payload)
                    rec_counts['wr'] += rc.get('wr', 0)
                    rec_counts['cr'] += rc.get('cr', 0)
                    rec_counts['nr'] += rc.get('nr', 0)
                except Exception:
                    pass
                medals_block = payload.get('medals') if isinstance(payload, dict) else None
                if isinstance(medals_block, dict):
                    g = medals_block.get('gold'); s = medals_block.get('silver'); b = medals_block.get('bronze')
                    try:
                        g = int(g) if g is not None else None
                        s = int(s) if s is not None else None
                        b = int(b) if b is not None else None
                    except Exception:
                        g = s = b = None
                    if isinstance(g, int): totals['gold'] = g
                    if isinstance(s, int): totals['silver'] = s
                    if isinstance(b, int): totals['bronze'] = b
                    if any(isinstance(x, int) and x >= 0 for x in [g, s, b]):
                        found = True
            except Exception:
                pass
            # 2) API v0 persons/{id}
            if not found:
                try:
                    v0_url = f"https://www.worldcubeassociation.org/api/v0/persons/{wca_id}"
                    req2 = urllib.request.Request(v0_url, headers={
                        'User-Agent': 'Mozilla/5.0',
                        'Accept': 'application/json'
                    })
                    resp2 = urllib.request.urlopen(req2, timeout=10)
                    payload2 = json.loads(resp2.read())
                    if comp_count is None:
                        comp_count = _extract_competition_count(payload2)
                    try:
                        rc = _accumulate_record_counts(payload2)
                        rec_counts['wr'] += rc.get('wr', 0)
                        rec_counts['cr'] += rc.get('cr', 0)
                        rec_counts['nr'] += rc.get('nr', 0)
                    except Exception:
                        pass
                    for node in [payload2, payload2.get('person') if isinstance(payload2, dict) and isinstance(payload2.get('person'), dict) else None]:
                        if not isinstance(node, dict):
                            continue
                        medals_block = node.get('medals')
                        if isinstance(medals_block, dict):
                            g = medals_block.get('gold'); s = medals_block.get('silver'); b = medals_block.get('bronze')
                            try:
                                g = int(g) if g is not None else None
                                s = int(s) if s is not None else None
                                b = int(b) if b is not None else None
                            except Exception:
                                g = s = b = None
                            if isinstance(g, int): totals['gold'] = g
                            if isinstance(s, int): totals['silver'] = s
                            if isinstance(b, int): totals['bronze'] = b
                            if any(isinstance(x, int) and x >= 0 for x in [g, s, b]):
                                found = True
                except Exception:
                    pass
            comp['medals_gold'] = totals['gold'] if found or any(v > 0 for v in totals.values()) else None
            comp['medals_silver'] = totals['silver'] if found or any(v > 0 for v in totals.values()) else None
            comp['medals_bronze'] = totals['bronze'] if found or any(v > 0 for v in totals.values()) else None
            comp['medals_total'] = (totals['gold'] + totals['silver'] + totals['bronze']) if comp['medals_gold'] is not None else None
            comp['competition_count'] = comp_count if isinstance(comp_count, int) and comp_count >= 0 else comp.get('competition_count')
            total_recs = rec_counts['wr'] + rec_counts['cr'] + rec_counts['nr']
            comp['records_wr'] = rec_counts['wr'] if rec_counts['wr'] > 0 else None
            comp['records_cr'] = rec_counts['cr'] if rec_counts['cr'] > 0 else None
            comp['records_nr'] = rec_counts['nr'] if rec_counts['nr'] > 0 else None
            comp['records_total'] = total_recs if total_recs > 0 else None
        return items
    @app.route('/')
    def wcaHome():
        competitors = _famous_competitors()
        return render_template('wca.html', competitors=competitors, query='', error=None)
    
    # Upload de imagens
    
    @app.route('/galeria', methods=['GET', 'POST'])
    def galeria():
        return render_template('galeria.html')
        
    # WCA - Competidores (Consumo da API de busca de usuários)
    @app.route('/wca', methods=['GET'])
    def wcaCompetitors():
        query = request.args.get('q', '').strip()
        competitors = []
        error = None
        if query:
            try:
                encoded_q = urllib.parse.quote(query)
                wca_url = f"https://www.worldcubeassociation.org/api/v0/search/users?q={encoded_q}"
                response = urllib.request.urlopen(wca_url)
                data = response.read()
                json_data = json.loads(data)
                results = json_data.get('result') or json_data.get('results') or []
                for item in results:
                    if item.get('class') == 'user' or item.get('wca_id'):
                        avatar_obj = item.get('avatar') or {}
                        avatar_url = avatar_obj.get('url') if isinstance(avatar_obj, dict) else None
                        avatar_thumb_url = avatar_obj.get('thumb_url') if isinstance(avatar_obj, dict) else None

                        profile_url = None
                        if item.get('wca_id'):
                            profile_url = f"https://www.worldcubeassociation.org/persons/{item.get('wca_id')}"
                        elif item.get('url'):
                            raw_url = item.get('url')
                            profile_url = raw_url if raw_url.startswith('http') else f"https://www.worldcubeassociation.org{raw_url}"

                        competitors.append({
                            'name': item.get('name'),
                            'wca_id': item.get('wca_id'),
                            'country_iso2': item.get('country_iso2'),
                            'avatar_url': avatar_url,
                            'avatar_thumb_url': avatar_thumb_url,
                            'profile_url': profile_url,
                            'competition_count': None,
                            'medals_gold': None,
                            'medals_silver': None,
                            'medals_bronze': None,
                            'medals_total': None,
                            'records_wr': None,
                            'records_cr': None,
                            'records_nr': None,
                            'records_total': None
                        })

                def _to_int(val):
                    try:
                        if isinstance(val, bool):
                            return None
                        if isinstance(val, (int, float)):
                            return int(val)
                        if isinstance(val, str):
                            return int(val) if val.isdigit() else None
                    except Exception:
                        return None
                    return None

                def _accumulate_counts(target, container):
                    if not isinstance(container, dict):
                        return False
                    found_any = False
                    mapping = [
                        ('gold', ['gold', 'golds', 'first', '1', 'one']),
                        ('silver', ['silver', 'silvers', 'second', '2', 'two']),
                        ('bronze', ['bronze', 'bronzes', 'third', '3', 'three'])
                    ]
                    for key_out, candidates in mapping:
                        for cand in candidates:
                            if cand in container:
                                val = container.get(cand)
                                if isinstance(val, (int, float)):
                                    target[key_out] += int(val)
                                    found_any = True
                                    break
                    for nested_key in ['overall', 'summary', 'all', 'totals']:
                        nested = container.get(nested_key)
                        if isinstance(nested, dict):
                            if _accumulate_counts(target, nested):
                                found_any = True
                    for per_key in ['per_event', 'by_event', 'events']:
                        per = container.get(per_key)
                        if isinstance(per, dict):
                            for _, ev_val in per.items():
                                if isinstance(ev_val, dict):
                                    if _accumulate_counts(target, ev_val):
                                        found_any = True
                    return found_any

                def _accumulate_from_list(target, items):
                    if not isinstance(items, list):
                        return False
                    found_any = False
                    for it in items:
                        if not isinstance(it, dict):
                            continue
                        medal = (it.get('medal') or it.get('podium') or it.get('place_label'))
                        if isinstance(medal, str):
                            m = medal.strip().lower()
                            if 'gold' in m or m in ['1', 'first']:
                                target['gold'] += 1; found_any = True; continue
                            if 'silver' in m or m in ['2', 'second']:
                                target['silver'] += 1; found_any = True; continue
                            if 'bronze' in m or m in ['3', 'third']:
                                target['bronze'] += 1; found_any = True; continue
                        for pos_key in ['position', 'pos', 'rank', 'place', 'standing']:
                            pos_val = it.get(pos_key)
                            try:
                                pos_val_int = int(pos_val)
                            except Exception:
                                pos_val_int = None
                            if pos_val_int == 1:
                                target['gold'] += 1; found_any = True; break
                            if pos_val_int == 2:
                                target['silver'] += 1; found_any = True; break
                            if pos_val_int == 3:
                                target['bronze'] += 1; found_any = True; break
                    return found_any

                def _extract_competition_count(payload):
                    if not isinstance(payload, dict):
                        return None
                    for key in ['competition_count', 'competitions_count', 'num_competitions']:
                        num = payload.get(key)
                        try:
                            num = int(num)
                        except Exception:
                            num = None
                        if isinstance(num, int) and num >= 0:
                            return num
                    person = payload.get('person')
                    if isinstance(person, dict):
                        for key in ['competition_count', 'competitions_count', 'num_competitions']:
                            try:
                                num = int(person.get(key))
                            except Exception:
                                num = None
                            if isinstance(num, int) and num >= 0:
                                return num
                    for list_key in ['competitions', 'participations', 'competition_participations']:
                        lst = payload.get(list_key)
                        if isinstance(lst, list):
                            return len(lst)
                    return None

                for comp in competitors:
                    wca_id = comp.get('wca_id')
                    if not wca_id:
                        continue
                    comp_count = None
                    try:
                        totals = {'gold': 0, 'silver': 0, 'bronze': 0}
                        found = False

                        try:
                            official_url = f"https://www.worldcubeassociation.org/persons/{wca_id}.json"
                            req = urllib.request.Request(official_url, headers={
                                'User-Agent': 'Mozilla/5.0',
                                'Accept': 'application/json'
                            })
                            resp = urllib.request.urlopen(req, timeout=10)
                            payload = json.loads(resp.read())
                            if comp_count is None:
                                comp_count = _extract_competition_count(payload)
                            if isinstance(payload, dict):
                                medals_block = payload.get('medals')
                                if isinstance(medals_block, dict):
                                    g = medals_block.get('gold')
                                    s = medals_block.get('silver')
                                    b = medals_block.get('bronze')
                                    try:
                                        g = int(g) if g is not None else None
                                        s = int(s) if s is not None else None
                                        b = int(b) if b is not None else None
                                    except Exception:
                                        g = s = b = None
                                    if isinstance(g, int): totals['gold'] = g
                                    if isinstance(s, int): totals['silver'] = s
                                    if isinstance(b, int): totals['bronze'] = b
                                    if any(isinstance(x, int) and x >= 0 for x in [g, s, b]):
                                        found = True
                                if not found and _accumulate_counts(totals, payload):
                                    found = True
                        except Exception:
                            pass

                        if not found:
                            try:
                                v0_url = f"https://www.worldcubeassociation.org/api/v0/persons/{wca_id}"
                                req2 = urllib.request.Request(v0_url, headers={
                                    'User-Agent': 'Mozilla/5.0',
                                    'Accept': 'application/json'
                                })
                                resp2 = urllib.request.urlopen(req2, timeout=10)
                                payload2 = json.loads(resp2.read())
                                if comp_count is None:
                                    comp_count = _extract_competition_count(payload2)
                                if isinstance(payload2, dict):
                                    for node in [payload2, payload2.get('person') if isinstance(payload2.get('person'), dict) else None]:
                                        if not isinstance(node, dict):
                                            continue
                                        if comp_count is None:
                                            comp_count = _extract_competition_count(node)
                                        medals_block = node.get('medals')
                                        if isinstance(medals_block, dict):
                                            g = medals_block.get('gold')
                                            s = medals_block.get('silver')
                                            b = medals_block.get('bronze')
                                            try:
                                                g = int(g) if g is not None else None
                                                s = int(s) if s is not None else None
                                                b = int(b) if b is not None else None
                                            except Exception:
                                                g = s = b = None
                                            if isinstance(g, int): totals['gold'] = g
                                            if isinstance(s, int): totals['silver'] = s
                                            if isinstance(b, int): totals['bronze'] = b
                                            if any(isinstance(x, int) and x >= 0 for x in [g, s, b]):
                                                found = True
                                    if not found and _accumulate_counts(totals, payload2):
                                        found = True
                            except Exception:
                                pass

                        if not found:
                            podiums_url = f"https://wca-rest-api.robiningelbrecht.be/persons/{wca_id}/podiums"
                            try:
                                resp = urllib.request.urlopen(podiums_url, timeout=5)
                                payload = json.loads(resp.read())
                                if comp_count is None:
                                    comp_count = _extract_competition_count(payload)
                                if isinstance(payload, dict):
                                    if _accumulate_counts(totals, payload):
                                        found = True
                                    for key in ['data', 'items', 'podiums', 'results', 'list']:
                                        if key in payload:
                                            items = payload.get(key)
                                            if isinstance(items, list):
                                                if _accumulate_from_list(totals, items):
                                                    found = True
                                elif isinstance(payload, list):
                                    if _accumulate_from_list(totals, payload):
                                        found = True
                            except Exception:
                                pass

                        if not found:
                            person_url = f"https://wca-rest-api.robiningelbrecht.be/persons/{wca_id}"
                            try:
                                resp = urllib.request.urlopen(person_url, timeout=5)
                                payload = json.loads(resp.read())
                                if comp_count is None:
                                    comp_count = _extract_competition_count(payload)
                                if isinstance(payload, dict):
                                    for key in ['medals', 'podiums']:
                                        if key in payload:
                                            if _accumulate_counts(totals, payload.get(key)):
                                                found = True
                                    if _accumulate_counts(totals, payload):
                                        found = True
                                    for key in ['podiums', 'results', 'items']:
                                        if key in payload:
                                            items = payload.get(key)
                                            if isinstance(items, list):
                                                if _accumulate_from_list(totals, items):
                                                    found = True
                            except Exception:
                                pass

                        comp['medals_gold'] = totals['gold'] if found or any(v > 0 for v in totals.values()) else None
                        comp['medals_silver'] = totals['silver'] if found or any(v > 0 for v in totals.values()) else None
                        comp['medals_bronze'] = totals['bronze'] if found or any(v > 0 for v in totals.values()) else None
                        comp['medals_total'] = (totals['gold'] + totals['silver'] + totals['bronze']) if comp['medals_gold'] is not None else None
                        comp['competition_count'] = comp_count if isinstance(comp_count, int) and comp_count >= 0 else None
                        # Extrair recordes do payloads já buscados quando possível
                        try:
                            rec_counts = {'wr': 0, 'cr': 0, 'nr': 0}
                            def _accumulate_record_counts(payload):
                                counts = {'wr': 0, 'cr': 0, 'nr': 0}
                                if not isinstance(payload, dict):
                                    return counts
                                records = payload.get('records') or payload.get('current_records') or payload.get('record')
                                def walk(node):
                                    if isinstance(node, dict):
                                        for k, v in node.items():
                                            key = str(k).lower()
                                            if key in ['world', 'wr']:
                                                try:
                                                    if isinstance(v, (int, float)) and int(v) > 0: counts['wr'] += int(v)
                                                    elif isinstance(v, (str, bytes)) and v: counts['wr'] += 1
                                                    elif isinstance(v, bool) and v: counts['wr'] += 1
                                                    elif isinstance(v, dict) or isinstance(v, list):
                                                        before = counts['wr']; walk(v); counts['wr'] += 0 if counts['wr'] == before else 0
                                                except Exception:
                                                    pass
                                            if key in ['continental', 'continent', 'cr']:
                                                try:
                                                    if isinstance(v, (int, float)) and int(v) > 0: counts['cr'] += int(v)
                                                    elif isinstance(v, (str, bytes)) and v: counts['cr'] += 1
                                                    elif isinstance(v, bool) and v: counts['cr'] += 1
                                                    elif isinstance(v, dict) or isinstance(v, list):
                                                        before = counts['cr']; walk(v); counts['cr'] += 0 if counts['cr'] == before else 0
                                                except Exception:
                                                    pass
                                            if key in ['national', 'country', 'nr']:
                                                try:
                                                    if isinstance(v, (int, float)) and int(v) > 0: counts['nr'] += int(v)
                                                    elif isinstance(v, (str, bytes)) and v: counts['nr'] += 1
                                                    elif isinstance(v, bool) and v: counts['nr'] += 1
                                                    elif isinstance(v, dict) or isinstance(v, list):
                                                        before = counts['nr']; walk(v); counts['nr'] += 0 if counts['nr'] == before else 0
                                                except Exception:
                                                    pass
                                            walk(v)
                                    elif isinstance(node, list):
                                        for it in node:
                                            walk(it)
                                if isinstance(records, (dict, list)):
                                    walk(records)
                                else:
                                    walk(payload)
                                return counts
                            # Try from last payloads
                            try:
                                rc = _accumulate_record_counts(payload)
                                rec_counts['wr'] += rc.get('wr', 0)
                                rec_counts['cr'] += rc.get('cr', 0)
                                rec_counts['nr'] += rc.get('nr', 0)
                            except Exception:
                                pass
                            try:
                                rc2 = _accumulate_record_counts(payload2)
                                rec_counts['wr'] += rc2.get('wr', 0)
                                rec_counts['cr'] += rc2.get('cr', 0)
                                rec_counts['nr'] += rc2.get('nr', 0)
                            except Exception:
                                pass
                            total_recs = rec_counts['wr'] + rec_counts['cr'] + rec_counts['nr']
                            comp['records_wr'] = rec_counts['wr'] if rec_counts['wr'] > 0 else None
                            comp['records_cr'] = rec_counts['cr'] if rec_counts['cr'] > 0 else None
                            comp['records_nr'] = rec_counts['nr'] if rec_counts['nr'] > 0 else None
                            comp['records_total'] = total_recs if total_recs > 0 else None
                        except Exception:
                            comp['records_wr'] = None
                            comp['records_cr'] = None
                            comp['records_nr'] = None
                            comp['records_total'] = None
                    except Exception:
                        comp['medals_gold'] = None
                        comp['medals_silver'] = None
                        comp['medals_bronze'] = None
                        comp['medals_total'] = None
                        comp['competition_count'] = None
            except Exception:
                error = 'Falha ao buscar dados na API da WCA.'
        else:
            competitors = _famous_competitors()
        return render_template('wca.html', competitors=competitors, query=query, error=error)