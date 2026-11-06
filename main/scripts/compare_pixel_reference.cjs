// Fixed-time physical RGB parity against a locally extracted 0.37 HTML asset.
const fs=require('node:fs'),assert=require('node:assert/strict');
const {studio,plain}=require('../beatlight/tests/studio-harness.cjs');
const source=fs.readFileSync(process.argv[2],'utf8').match(/<script>([\s\S]*?)<\/script>/)[1];
function setup(sourceOverride){const app=studio({embedded:true,random:()=>.37,sourceOverride});app.page.prepareWs2812(app.page.project().strips[0].id,300);app.page.setInput('demo');app.page.arm(true);return app;}
const before=setup(source),after=setup();let frames=0;
const modes=['ambient','pulse','chase','mirror','wave','helix','rain','drop','comet','scanner','sparkle','meteor','fire','rainbow','blocks','bounce','ripple','equalizer','snake','aurora','weave','orbit','shards','tide','lattice','vortex','wash','breathe','gradient','colorflow','liquid','crossflow','chromatide','auto','organic'];
for(const [i,mode] of modes.entries()){
  const project=plain(before.page.project());project.show.mode=mode;
  before.page.applyProject(project);after.page.applyProject(project);
  for(let sample=0;sample<4;sample++){
    const time=(i*4+sample)*157;before.clock(time);after.clock(time);
    const id=project.strips[0].id;
    assert.deepEqual(plain(after.page.outputFrame(id)),plain(before.page.outputFrame(id)),`${mode} at ${time}`);frames++;
  }
}
const report={passed:true,frames,modes:modes.length,physical_rgb_unchanged:true};
fs.writeFileSync(process.argv[3],JSON.stringify(report,null,2));console.log(JSON.stringify(report));
