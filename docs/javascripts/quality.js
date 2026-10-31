/* Display recorded test evidence separately from illustrative range overlays. */
(function () {
  'use strict';
  const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  const get=async url=>{const r=await fetch(url);if(!r.ok)throw new Error();return r.json();};
  // Group recorded pytest modules by what they protect; order is fixed, not by result.
  const purposes = [
    ['Release files, data contract and job safety', /test_(data_contract|dataset_release|release_lineage|memory_safe|reconversion|live_source_audit|backlog|review_sheet)/, 'Synthetic fixtures and code paths; no research files read.'],
    ['Website, previews and charts', /test_(data_documentation|data_preview|aggregate_previews|static_aggregate_preview|phase_chart|quality_page|ensemble_preview)/, 'Synthetic fixtures and the published static files.'],
    ['Review tools and previously found problems', /test_(tuner_review|review_regressions)/, 'Synthetic fixtures reproducing earlier defects.'],
    ['Shared converter logic and conventions', /test_(converter_scientific_provenance|phase_detection|standing_action|sign_offset)/, 'Synthetic signals with known answers.'],
    ['UMich 2021 conversion and source checks', /test_(umich|um21|audit_um21)/, 'Synthetic fixtures and small source excerpts.'],
    ['Georgia Tech 2021 conversion and source checks', /test_gt21/, 'Synthetic fixtures and small source excerpts.'],
    ['Georgia Tech 2023 conversion and source checks', /test_(gt23|gtech_2023)/, 'Synthetic fixtures and small source excerpts.'],
    ['Georgia Tech 2024 conversion and source checks', /test_gt24/, 'Synthetic fixtures and small source excerpts.'],
    ['Georgia Tech 2025 conversion and source checks', /test_gt25/, 'Synthetic fixtures and small source excerpts.'],
    ['MBLUE conversion and source checks', /test_mblue/, 'Synthetic fixtures and small source excerpts.'],
    ['Gait120 conversion and source checks', /test_gait120/, 'Synthetic fixtures and small source excerpts.'],
    ['StrokePiG conversion and source checks', /test_strokepig/, 'Synthetic fixtures and small source excerpts.'],
    ['Other dataset checks', /./, 'See the module list.']
  ];
  const purposeOf = name => purposes.findIndex(([, pattern]) => pattern.test(name.split('.').pop()));
  const day = value => { const d = new Date(String(value).slice(0, 10) + 'T00:00:00Z'); return isNaN(d) ? 'an unrecorded date' : d.toLocaleDateString('en-GB', {day:'numeric', month:'long', year:'numeric', timeZone:'UTC'}); };
  const testRoot=document.getElementById('quality-test-results');
  get(testRoot.dataset.source).then(report=>{
    testRoot.replaceChildren();
    const totals=report.totals;
    testRoot.append(node('p',`Recorded run of ${day(report.started_at || report.recorded_at)}: ${totals.passed} passed, ${totals.failed} failed, ${totals.skipped} not run. ${report.scope}`));
    if(Array.isArray(report.repository_test_modules)){
      const recorded=new Set(Object.keys(report.groups).map(n=>n.split('.').pop()));
      const absent=report.repository_test_modules.filter(m=>!recorded.has(m));
      if(absent.length) testRoot.append(node('p',`${absent.length} of ${report.repository_test_modules.length} test files in the repository at that time are not in this record, so they count as unassessed.`,'audit-limitation'));
    }
    const rows=purposes.map(([label,,scope])=>({label,scope,passed:0,failed:0,skipped:0,modules:[]}));
    Object.entries(report.groups).forEach(([name,group])=>{const r=rows[purposeOf(name)];['passed','failed','skipped'].forEach(k=>r[k]+=group[k]);r.modules.push([name,group]);});
    const table=node('table'),head=node('thead'),hr=node('tr'),body=node('tbody');
    table.append(node('caption','Recorded software tests by purpose'));
    ['What the tests protect (scope)','Passed','Failed','Not run'].forEach(t=>{const th=node('th',t);th.scope='col';hr.append(th);});head.append(hr);table.append(head);
    rows.filter(r=>r.modules.length).forEach(r=>{
      const tr=node('tr'),th=node('th',r.label);th.scope='row';th.append(node('small',r.scope,'test-scope'));tr.append(th);
      [r.passed,r.failed,r.skipped].forEach(n=>tr.append(node('td',String(n),'num')));body.append(tr);
    });
    table.append(body);const wrap=node('div',undefined,'table-scroll test-summary');wrap.setAttribute('role','region');wrap.setAttribute('tabindex','0');wrap.setAttribute('aria-label','Recorded software tests by purpose');wrap.append(table);testRoot.append(wrap);
    const skipped=Object.values(report.groups).flatMap(g=>g.cases).filter(t=>t.status==='skipped');
    if(skipped.length){const list=node('ul');skipped.forEach(t=>list.append(node('li',`${t.name}: ${t.reason || 'no reason recorded'}`)));const d=node('details');d.append(node('summary',`Why ${skipped.length} test${skipped.length===1?' was':'s were'} not run`),list);testRoot.append(d);}
    const all=node('details');all.append(node('summary','Every recorded test, by module'));
    rows.filter(r=>r.modules.length).forEach(r=>{
      all.append(node('h3',r.label,'test-purpose'));
      r.modules.sort((a,b)=>a[0].localeCompare(b[0])).forEach(([name,group])=>{
        const details=node('details');details.append(node('summary',`${name.replace(/^tests\./,'')}: ${group.passed} passed, ${group.failed} failed, ${group.skipped} not run`));
        const list=node('ul');[...group.cases].sort((a,b)=>({failed:0,skipped:1,passed:2}[a.status]-{failed:0,skipped:1,passed:2}[b.status])).forEach(test=>list.append(node('li',`${test.status}: ${test.name}${test.reason?' ('+test.reason+')':''}`)));details.append(list);all.append(details);
      });
    });
    testRoot.append(all);
    const provenance=node('details');provenance.append(node('summary','When and how these software tests ran'));
    provenance.append(node('p',`Suite timestamp: ${report.started_at || 'Not recorded'}. Report file modified: ${report.recorded_at}.`),node('p',`Base revision: ${report.base_revision}. Tracked working-tree changes: ${report.working_tree_changes ? 'yes; this is not a clean commit snapshot' : 'no'}. Untracked inputs are not captured by this flag.`),node('p',`JUnit SHA-256: ${report.junit_sha256}`));
    if(report.command){const command=node('pre');command.append(node('code',report.command));provenance.append(command);}else provenance.append(node('p','Invocation was not recorded.'));
    testRoot.append(provenance);
  }).catch(()=>{testRoot.textContent='Recorded results could not be loaded. Use the JSON download below.';});
  const filter=document.getElementById('audit-dataset-filter');
  const auditRows=[...document.querySelectorAll('.audit-table tbody tr')];
  const families=new Map(auditRows.map(row=>[row.dataset.auditDataset,row.querySelector('.audit-dataset-name').textContent]));
  families.forEach((name,slug)=>filter.add(new Option(name,slug)));
  filter.parentElement.hidden=false;
  filter.onchange=()=>{
    document.querySelectorAll('[data-audit-dataset]').forEach(el=>{el.hidden=el.classList.contains('audit-evidence') || (!!filter.value && el.dataset.auditDataset!==filter.value);if(el.classList.contains('audit-evidence'))el.open=false;});
    document.getElementById('audit-filter-status').textContent=`${auditRows.filter(r=>!r.hidden).length} files. Select a file to see its findings.`;
  };
  function openEvidence(){
    const detail=document.getElementById(location.hash.slice(1));
    if(detail?.classList.contains('audit-evidence')){
      filter.value=detail.dataset.auditDataset;filter.onchange();
      detail.hidden=false;detail.open=true;detail.querySelector('summary').focus();
    }
  }
  filter.value='um21';filter.onchange();
  document.querySelectorAll('.audit-table a').forEach(link=>link.addEventListener('click',()=>{if(link.hash===location.hash)openEvidence();}));
  window.addEventListener('hashchange',openEvidence);openEvidence();
  document.querySelectorAll('.quality-nav a').forEach(link=>link.addEventListener('click',()=>{const target=document.querySelector(link.hash);if(target?.tagName==='DETAILS')target.open=true;}));
  const panel=document.getElementById('quality-phase'),select=document.getElementById('quality-dataset');
  let profile,manifest,change=0;const lineage={};
  const fileName=url=>{try{return url?decodeURIComponent(new URL(url).pathname.split('/').pop()):undefined;}catch(_){return undefined;}};
  async function mount() {
    const current=++change;window.LocoHubAverages.dispose();panel.replaceChildren();
    if(!select.value){panel.append(node('p','Choose a dataset to explore its averages and configured bounds.'));return;}
    const meta=node('p',undefined,'phase-source'),note=node('p','Loading averages…','phase-note'),controls=node('div'),plot=node('div');panel.append(meta,note,controls,plot);
    await window.LocoHubAverages.mount({panel,slug:select.value,anchor:panel,controls,plot,meta,note,stopRawChart(){},rangeProfile:profile,lineage:lineage[select.value]});
    if(current!==change)return;
    if(!panel.querySelector('.aggregate-preview')) {
      note.textContent=manifest.datasets[select.value]?.tasks?.length?'Averages could not be loaded.':'No numerical preview is available for this study.';
      const retry=node('button','Retry','button');retry.type='button';retry.onclick=mount;panel.append(retry);
    }
  }
  async function initialize() {
    try {
      profile=await get('phase_ranges.json');manifest=await get(panel.dataset.aggregateSource);
      const catalog=await get('../datasets/comparison_data.json');
      const table=node('table'),head=node('thead'),row=node('tr'),body=node('tbody');
      ['Dataset','Preview input (legacy local file)','Same name as a download?','Curves averaged','Blocks not used','Tasks previewed'].forEach(t=>{const th=node('th',t);th.scope='col';row.append(th);});head.append(row);table.append(node('caption','Preview inputs and coverage. Curves are 150-point blocks used for plots, not counts of passing or independent observations.'),head);
      catalog.datasets.forEach(d=>{
        select.add(new Option(d.display_name,d.slug));const dataset=manifest.datasets[d.slug],c=dataset?.excluded_counts,file=dataset?.source?.filename;
        const full=fileName(d.dirty_url),filtered=fileName(d.clean_url),listed=(d.tasks||[]).length;lineage[d.slug]={full,filtered,catalogTasks:listed};
        const excluded=c?Object.entries(c).filter(([k])=>k.endsWith('_observations')&&k!=='complete_observations').reduce((n,[,v])=>n+v,0):null;
        const match=!file?'—':file===full?'Full download (bytes not compared)':file===filtered?'Filtered download (bytes not compared)':'No';
        const tr=node('tr'),th=node('th',d.display_name);th.scope='row';tr.append(th);
        [file || (dataset?.reason || 'No input recorded'),match,c?c.complete_observations.toLocaleString():'Not recorded',excluded===null?'Not recorded':String(excluded),`${dataset?.tasks?.length || 0} of ${listed}`].forEach(t=>tr.append(node('td',t)));body.append(tr);
      });table.append(body);const wrap=node('div',undefined,'table-scroll');wrap.setAttribute('role','region');wrap.setAttribute('tabindex','0');wrap.setAttribute('aria-label','Preview preparation counts');wrap.append(table);document.getElementById('quality-coverage').replaceChildren(wrap);
      document.getElementById('quality-profile-source').textContent=`Range source: ${profile.source}. SHA-256: ${profile.sha256}.`;
      select.value='';select.onchange=mount;await mount();
    } catch(error) {
      panel.replaceChildren(node('p','Configured ranges or summary metadata could not be loaded.'));
      const retry=node('button','Retry','button');retry.type='button';retry.onclick=()=>location.reload();panel.append(retry);
      document.getElementById('quality-coverage').textContent='Preview coverage could not be loaded.';
    }
  }
  initialize();
})();
