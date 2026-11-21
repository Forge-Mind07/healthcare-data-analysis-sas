// Standard ECharts SSR + Sharp reference plots. These are NOT SAS screenshots.
import { createRequire } from 'node:module';
import { readFile, writeFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const require = createRequire(import.meta.url);
const echarts = require('echarts');
const sharp = require('sharp');
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');

// Aggregate CSVs use RFC 4180 escaping. No patient-level input is read here.
function parseCSV(text) {
  const rows=[]; let row=[], field='', quoted=false;
  for(let i=0;i<text.length;i++) {
    const c=text[i];
    if(c==='"') { if(quoted && text[i+1]==='"') {field+='"'; i++;} else quoted=!quoted; }
    else if(c===',' && !quoted) {row.push(field);field='';}
    else if(c==='\n' && !quoted) {row.push(field.replace(/\r$/, ''));rows.push(row);row=[];field='';}
    else field+=c;
  }
  if(field || row.length) {row.push(field);rows.push(row);}
  const [header,...body]=rows;
  return body.filter(r=>r.length===header.length).map(r=>Object.fromEntries(header.map((h,i)=>[h,r[i]])));
}
async function csv(name) {return parseCSV(await readFile(resolve(root,'results',name),'utf8'));}
const manifest=JSON.parse(await readFile(resolve(root,'results/validation_manifest.json'),'utf8'));
const receipt=JSON.parse(await readFile(resolve(root,'results/sql_validation.json'),'utf8'));
if(receipt.status!=='PASS' || receipt.source_file_sha256!==manifest.source_file_sha256) throw Error('SQL verification required');
const blue='#315f85';
async function chart(name,title,xlabel,ylabel,labels,values,{max,barWidth}={}) {
  if(!values.every(Number.isFinite)) throw Error('Invalid chart values');
  const instance=echarts.init(null,null,{renderer:'svg',ssr:true,width:1440,height:850});
  instance.setOption({animation:false,backgroundColor:'#ffffff',
    title:{text:title,subtext:`Cleaned population N = ${manifest.cleaned_n.toLocaleString('en-US')}`,left:65,top:30,
      textStyle:{fontFamily:'DejaVu Sans',fontSize:27,color:'#132538'},subtextStyle:{fontSize:17,color:'#526172'}},
    grid:{left:130,right:55,top:155,bottom:170},
    xAxis:{type:'category',data:labels,name:xlabel,nameLocation:'middle',nameGap:68,
      nameTextStyle:{fontSize:18},axisLabel:{fontSize:15,rotate:labels.length>35 ? 45:0,interval:labels.length>35 ? 4:0}},
    yAxis:{type:'value',min:0,...(max?{max}:{}),name:ylabel,nameLocation:'middle',nameGap:90,
      nameTextStyle:{fontSize:18},axisLabel:{fontSize:15},splitLine:{lineStyle:{color:'#e1e6eb'}}},
    series:[{type:'bar',data:values,itemStyle:{color:blue},...(barWidth?{barWidth}:{}),
      label:{show:labels.length<10,position:'top',fontSize:15,formatter:p=>Number(p.value).toLocaleString('en-US',{maximumFractionDigits:2})}}],
    graphic:[{type:'text',left:65,bottom:25,style:{text:'Independent reference chart generated with ECharts — not SAS output\nDescriptive analysis only • Billing currency unspecified',font:'15px DejaVu Sans',fill:'#526172',lineHeight:23}}]
  });
  const png=await sharp(Buffer.from(instance.renderToSVGString())).png().toBuffer();
  await writeFile(resolve(root,'visuals',name+'.png'),png);instance.dispose();
  return {file:`visuals/${name}.png`,labels,values,axis_minimum:0,axis_maximum:max??null,engine:'ECharts SVG renderer + Sharp PNG'};
}
const billing=await csv('condition_billing_summary.csv');
const abnormal=await csv('abnormal_test_results.csv');
const stays=await csv('hospital_stay_days_distribution.csv');
const byCondition=await csv('condition_stay_summary.csv');
const ages=await csv('age_distribution.csv');
const series=[];
series.push(await chart('average_billing_by_condition','Average billing by medical condition','Medical condition','Average billing amount',billing.map(r=>r.condition),billing.map(r=>+r.mean)));
series.push(await chart('abnormal_test_results','Abnormal test results within each condition','Medical condition','Abnormal results (%)',abnormal.map(r=>r.condition),abnormal.map(r=>+r.abnormal_percent),{max:100}));
series.push(await chart('hospital_stay_distribution','Distribution of hospital stay duration','Hospital stay (days)','Number of admissions',stays.map(r=>String(+r.value)),stays.map(r=>+r.n)));
series.push(await chart('average_stay_by_condition','Average hospital stay by medical condition','Medical condition','Average hospital stay (days)',byCondition.map(r=>r.condition),byCondition.map(r=>+r.mean)));
const bins=[];
for(let start=0;start<120;start+=5) {const n=ages.filter(r=>+r.value>=start && +r.value<start+5).reduce((sum,r)=>sum+(+r.n),0);if(n || (start>=10 && start<=85)) bins.push({label:`${start}–${start+4}`,n});}
if(bins.reduce((s,r)=>s+r.n,0)!==manifest.cleaned_n) throw Error('Age bins do not reconcile');
series.push(await chart('patient_age_distribution','Age distribution in the cleaned population','Age in years (5-year bins)','Number of admissions',bins.map(r=>r.label),bins.map(r=>r.n)));
await writeFile(resolve(root,'results/chart_manifest.json'),JSON.stringify({reference_only:true,source_file_sha256:manifest.source_file_sha256,charts:series},null,2)+'\n');
console.log(`Generated and reconciled ${series.length} reference PNG charts`);
