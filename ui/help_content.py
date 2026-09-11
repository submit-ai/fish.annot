HELP_HTML = """
<style>
  body  { font-family:'Segoe UI'; font-size:10pt; color:#1F2933; margin:0; padding:0; }
  h1    { font-size:14pt; font-weight:bold; color:#1A365D; margin-top:0; margin-bottom:4px; }
  h2    { font-size:10pt; font-weight:bold; color:#2B6CB0; margin-top:18px; margin-bottom:4px; }
  p     { margin:3px 0; line-height:1.6; }
  table { border-collapse:collapse; width:100%; margin:8px 0; }
  th    { background:#F5F7FA; color:#52606D; font-weight:bold; font-size:9pt;
          border:1px solid #D9E2EC; padding:5px 10px; text-align:left; }
  td    { border:1px solid #D9E2EC; padding:5px 10px; vertical-align:top; }
  code  { background:#F0F4F8; color:#2B6CB0; padding:1px 4px;
          border-radius:3px; font-family:Consolas; font-size:9pt; }
  .note { color:#52606D; font-style:italic; font-size:9pt; }
</style>

<h1>FISH Annot &mdash; User Guide</h1>
<p class="note">Manual species annotation tool for underwater video grid images (DOP protocol).</p>

<h2>1 &mdash; Open a drop folder</h2>
<p>Click <b>File &rarr; Open drop folder</b> and select a segment folder produced by the Prepare tab.</p>
<p>The folder must contain <code>planche_verticale.png</code> (the composite grid image) and <code>metadata.json</code> (the grid structure).</p>
<p>If <code>annotations.csv</code> already exists in the folder, existing annotations are reloaded automatically.</p>

<h2>2 &mdash; Navigate the grid</h2>
<table>
  <tr><th>Action</th><th>Effect</th></tr>
  <tr><td>Click on a cell</td><td>Select it &mdash; cell metadata (camera, time, frame) appears in the right panel</td></tr>
  <tr><td>Double-click on a cell</td><td>Switch to HQ zoom on that cell and open the annotation form</td></tr>
  <tr><td>&uarr; / &darr;</td><td>Move to the previous / next row within the current column</td></tr>
  <tr><td>Escape</td><td>Return to full-grid overview</td></tr>
  <tr><td>Scroll wheel</td><td>Zoom in / out (~5 % per notch)</td></tr>
  <tr><td>Click and drag</td><td>Pan the image</td></tr>
  <tr><td><b>Overview</b> button</td><td>Fit the full grid to the window</td></tr>
  <tr><td><b>HQ Cell Zoom</b> button</td><td>Zoom into the currently selected cell</td></tr>
  <tr><td><b>Hide panel</b> button</td><td>Toggle the right annotation panel to gain screen space</td></tr>
</table>
<p class="note">In HQ mode, a red vertical guide splits the frame. It can be dragged with the mouse or set precisely via the <b>V</b> field (e.g. <code>30%</code>). Its position is saved automatically between sessions.</p>

<h2>3 &mdash; Annotate</h2>
<p>Switch to HQ cell zoom, then <b>click on the organism</b> to place an annotation point.</p>
<p>Select the <b>species</b> from the colour-coded dropdown (common name &mdash; scientific name).</p>
<p>Set the <b>count</b> if several individuals of the same species are visible at the same click area (default: 1).</p>
<p>Tick <b>Uncertain</b> if the identification is ambiguous &mdash; the annotation will be flagged in the table and highlighted in yellow in the Excel file.</p>
<p>Add an optional <b>comment</b> (e.g. behaviour, size, partial view).</p>
<p>Click <b>Add</b> to record. The annotation appears immediately as a coloured circle on the image.</p>
<p>Annotations are <b>auto-saved</b> after each action.</p>
<p>To correct an annotation: select its row in the table, modify the fields, and click <b>Update</b>.</p>
<p>To remove an annotation: select its row and click <b>Delete</b>.</p>
<p><b>Undo last annotation</b> removes the most recent entry without needing to select it.</p>

<h2>4 &mdash; Drop metadata</h2>
<p>Switch to the <b>Metadata</b> tab in the right panel to fill in drop-level context.</p>
<p>Available fields: Campaign &mdash; Location &mdash; Site &mdash; Drop ID &mdash; Date &mdash; Latitude &mdash; Longitude &mdash; Habitat &mdash; Depth &mdash; Visibility.</p>
<p>These fields are optional but recommended: they are added to every row of the annotation table and appear in the exported CSV and Excel files.</p>
<p>Click <b>Update metadata</b> to apply the current values to all existing annotations retroactively.</p>

<h2>5 &mdash; Species management</h2>
<p>Go to <b>File &rarr; Manage species</b> (or click <b>Manage species</b> in the annotation form) to add, remove, rename, or recolour species.</p>
<p>Each species has a common name, a scientific name, a family, a hex colour code, and an active/inactive flag.</p>
<p>Inactive species are hidden from the dropdown but kept in the database.</p>
<p>Changes are saved in <code>%APPDATA%\FISH Annot\species_config.json</code> — outside the installation folder, so updating or reinstalling the application keeps your list — and apply immediately to the current session and all future sessions.</p>

<h2>6 &mdash; Outputs</h2>
<p><b>Automatic &mdash; saved after every annotation action:</b></p>
<table>
  <tr><th>File</th><th>Description</th></tr>
  <tr>
    <td><code>annotations.csv</code></td>
    <td>Full annotation table (UTF-8 with BOM). One row per annotation.</td>
  </tr>
  <tr>
    <td><code>annotations.xlsx</code></td>
    <td>Same table in Excel format. Navy header, alternating row colours, uncertain annotations highlighted in yellow.</td>
  </tr>
</table>
<p><b>Optional &mdash; generated on demand:</b></p>
<table>
  <tr><th>File</th><th>How to generate</th><th>Description</th></tr>
  <tr>
    <td><code>planche_annotated.png</code></td>
    <td>Click <b>Generate annotated board</b></td>
    <td>Copy of the grid with coloured circles and species labels overlaid.</td>
  </tr>
  <tr>
    <td><code>crops/&lt;scientific_name&gt;/</code></td>
    <td><b>File &rarr; Export crops by species</b></td>
    <td>One image crop per annotation, cut from the full-resolution source frames. Uses an external detection box when one is provided, otherwise a 200&times;200 px square centred on the click.</td>
  </tr>
</table>

<h2>7 &mdash; Prepare tab</h2>
<p>Use the <b>Prepare</b> tab to generate annotation folders directly from raw videos or images.</p>
<p><b>From videos:</b> select one or more video files, configure the extraction interval and frames per segment, and the tool generates the <code>planche_verticale.png + metadata.json</code> segments ready to open in the Annotate tab.</p>
<p><b>From images:</b> select one or more image files and configure the grid layout (nx &times; ny) to generate planches.</p>

<h2>8 &mdash; Tips</h2>
<p>Use the <b>Zoom</b> field to type an exact zoom level (e.g. <code>150%</code>).</p>
<p>Use the <b>V</b> field to set the red guide position precisely (e.g. <code>33%</code>).</p>
<p>The grid overview is displayed at reduced resolution for performance. HQ zoom always loads the full-resolution cell.</p>
"""
