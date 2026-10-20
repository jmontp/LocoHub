/* Display recorded test evidence separately from illustrative range overlays. */
(function () {
  'use strict';
  const node=(tag,text,cls)=>{const e=document.createElement(tag);if(text!==undefined)e.textContent=text;if(cls)e.className=cls;return e;};
  const get=async url=>{const r=await fetch(url);if(!r.ok)throw new Error();return r.json();};
  const groupNames = {
    test_aggregate_previews: 'Subject-balanced averages', test_converter_scientific_provenance: 'Converter source mappings and conventions',
    test_data_contract: 'Data structure, identity and quality rules', test_data_documentation: 'Documentation and native examples',
    test_data_preview: 'Small preview samples', test_dataset_release: 'Release files, hashes and filtering',
    test_gtech_2023_time_conventions: 'Georgia Tech 2023 time-series conventions', test_memory_safe_parquet_tools: 'Memory-bounded file tools',
    test_phase_chart: 'Chart units, scales and missing values', test_quality_page: 'Published quality evidence and range boxes',
    test_reconversion_runner: 'Bounded conversion jobs', test_review_regressions: 'Previously found data-quality problems',
    test_static_aggregate_preview: 'Published averages and linked data', test_tuner_review_safeguards: 'Range editing and review safeguards',
    test_umich_2021_conventions: 'Michigan 2021 conversion conventions'
  };
  const testRoot=document.getElementById('quality-test-results');
  get(testRoot.dataset.source).then(report=>{
    testRoot.replaceChildren();
    testRoot.append(node('p',`${report.totals.passed} passed, ${report.totals.failed} failed, ${report.totals.skipped} skipped. ${report.scope}`));
    const skipped=Object.values(report.groups).flatMap(g=>g.cases).filter(t=>t.status==='skipped');
    skipped.forEach(t=>testRoot.append(node('p',`Not run: ${t.name} — ${t.reason || 'No reason recorded'}`,'audit-limitation')));
    const provenance=node('details');provenance.append(node('summary','When and how these software tests ran'));
    provenance.append(node('p',`Suite timestamp: ${report.started_at || 'Not recorded'}. Report file modified: ${report.recorded_at}.`),node('p',`Base revision: ${report.base_revision}. Tracked working-tree changes: ${report.working_tree_changes ? 'yes; this is not a clean commit snapshot' : 'no'}. Untracked inputs are not captured by this flag.`),node('p',`JUnit SHA-256: ${report.junit_sha256}`));
    if(report.command){const command=node('pre');command.append(node('code',report.command));provenance.append(command);}else provenance.append(node('p','Invocation was not recorded.'));
    testRoot.append(provenance);
    Object.entries(report.groups).sort((a,b)=>b[1].failed-a[1].failed || b[1].skipped-a[1].skipped || a[0].localeCompare(b[0])).forEach(([name,group])=>{
      const details=node('details'),summary=node('summary',`${groupNames[name.split('.').pop()] || name.replace(/^tests\./,'')} — ${group.passed} passed, ${group.failed} failed, ${group.skipped} skipped`);details.append(summary);
      const list=node('ul');[...group.cases].sort((a,b)=>({failed:0,skipped:1,passed:2}[a.status]-{failed:0,skipped:1,passed:2}[b.status])).forEach(test=>list.append(node('li',`${test.status}: ${test.name}${test.reason?' — '+test.reason:''}`)));details.append(list);testRoot.append(details);
    });
  }).catch(()=>{testRoot.textContent='Recorded results could not be loaded. Use the JSON download below.';});
  const filter=document.getElementById('audit-dataset-filter');
  const auditRows=[...document.querySelectorAll('.audit-table tbody tr')];
  const families=new Map(auditRows.map(row=>[row.dataset.auditDataset,row.querySelector('.audit-dataset-name').textContent]));
  families.forEach((name,slug)=>filter.add(new Option(name,slug)));
  filter.parentElement.hidden=false;
  filter.onchange=()=>{
    document.querySelectorAll('[data-audit-dataset]').forEach(el=>{el.hidden=!!filter.value && el.dataset.auditDataset!==filter.value;});
    document.getElementById('audit-filter-status').textContent=`${auditRows.filter(r=>!r.hidden).length} local files shown. No file has release approval from this audit.`;
  };
  function openEvidence(){
    const detail=document.getElementById(location.hash.slice(1));
    if(detail?.classList.contains('audit-evidence')){
      if(detail.hidden){filter.value=detail.dataset.auditDataset;filter.onchange();}
      detail.open=true;detail.querySelector('summary').focus();
    }
  }
  window.addEventListener('hashchange',openEvidence);openEvidence();
  const panel=document.getElementById('quality-phase'),select=document.getElementById('quality-dataset');
  let profile,manifest,change=0;
  async function mount() {
    const current=++change;window.LocoHubAverages.dispose();panel.replaceChildren();
    if(!select.value){panel.append(node('p','Choose a dataset to explore its averages and configured bounds.'));return;}
    const meta=node('p',undefined,'phase-source'),note=node('p','Loading averages…','phase-note'),controls=node('div'),plot=node('div');panel.append(meta,note,controls,plot);
    await window.LocoHubAverages.mount({panel,slug:select.value,anchor:panel,controls,plot,meta,note,stopRawChart(){},rangeProfile:profile});
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
      ['Dataset / preview input','150-point blocks used','Blocks not used for plots','Numerical summaries'].forEach(t=>{const th=node('th',t);th.scope='col';row.append(th);});head.append(row);table.append(node('caption','Preview preparation counts — not counts of passing observations'),head);
      catalog.datasets.forEach(d=>{
        select.add(new Option(d.display_name,d.slug));const dataset=manifest.datasets[d.slug],c=dataset?.excluded_counts;
        const excluded=c?Object.entries(c).filter(([k])=>k.endsWith('_observations')&&k!=='complete_observations').reduce((n,[,v])=>n+v,0):null;
        const tr=node('tr');[`${d.display_name} — ${dataset?.source?.filename || 'No input recorded'}`,c?c.complete_observations.toLocaleString():'Not recorded',excluded===null?'Not recorded':String(excluded),dataset?.tasks?.length?`${dataset.tasks.length} tasks`:'Unavailable'].forEach(t=>tr.append(node('td',t)));body.append(tr);
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
