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
    testRoot.replaceChildren();const counts=node('div',undefined,'quality-summary');
    ['passed','failed','skipped'].forEach(state=>{const p=node('p');p.append(node('strong',String(report.totals[state])),document.createTextNode(state));counts.append(p);});
    testRoot.append(counts,node('p',`Recorded ${new Date(report.recorded_at).toLocaleString()}. ${report.scope}`));
    Object.entries(report.groups).sort().forEach(([name,group])=>{
      const details=node('details'),summary=node('summary',`${groupNames[name.split('.').pop()] || name.replace(/^tests\./,'')} — ${group.passed} passed, ${group.failed} failed, ${group.skipped} skipped`);details.append(summary);
      const list=node('ul');group.cases.forEach(test=>list.append(node('li',`${test.status}: ${test.name}${test.reason?' — '+test.reason:''}`)));details.append(list);testRoot.append(details);
    });
    const command=node('pre');command.append(node('code',report.command));testRoot.append(command);
  }).catch(()=>{testRoot.textContent='Recorded results could not be loaded. Use the JSON download below.';});
  const panel=document.getElementById('quality-phase'),select=document.getElementById('quality-dataset');
  let profile,manifest,change=0;
  async function mount() {
    const current=++change;window.LocoHubAverages.dispose();panel.replaceChildren();
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
      ['Dataset','Complete curves','Excluded blocks','Numerical summaries'].forEach(t=>{const th=node('th',t);th.scope='col';row.append(th);});head.append(row);table.append(head);
      catalog.datasets.forEach(d=>{
        select.add(new Option(d.display_name,d.slug));const dataset=manifest.datasets[d.slug],c=dataset?.excluded_counts;
        const excluded=c?Object.entries(c).filter(([k])=>k.endsWith('_observations')&&k!=='complete_observations').reduce((n,[,v])=>n+v,0):null;
        const tr=node('tr');[d.display_name,c?c.complete_observations.toLocaleString():'Not recorded',excluded===null?'Not recorded':String(excluded),dataset?.tasks?.length?`${dataset.tasks.length} tasks`:'Unavailable'].forEach(t=>tr.append(node('td',t)));body.append(tr);
      });table.append(body);const wrap=node('div',undefined,'table-scroll');wrap.append(table);document.getElementById('quality-coverage').replaceChildren(wrap);
      document.getElementById('quality-profile-source').textContent=`Range source: ${profile.source}. SHA-256: ${profile.sha256}.`;
      select.value='ga26';select.onchange=mount;await mount();
    } catch(error) {
      panel.replaceChildren(node('p','Configured ranges or summary metadata could not be loaded.'));
      const retry=node('button','Retry','button');retry.type='button';retry.onclick=()=>location.reload();panel.append(retry);
      document.getElementById('quality-coverage').textContent='Preview coverage could not be loaded.';
    }
  }
  initialize();
})();
