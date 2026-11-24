export const gateViewTemplate = `
<section class="panel">
  <h2>闸口放行</h2>
  <p class="hint">无最新闸代快照禁放行（甲路径·当日锁死）：先在快照页封闸写最新代，本页方可放行；缺失即整笔回滚、正式册零增。旁路未闭环不得抬杆。</p>
  <div v-if="releasesMissingSnapshot.length" class="detail-box recon-warn">
    闸口警示：{{ releasesMissingSnapshot.length }} 条正式放行缺失最新闸代快照，须回滚补快照，不得判齐套。
  </div>
  <div class="form-row">
    <div><label>过磅票（仅列已封闸待放行）</label>
      <select v-model.number="gateForm.ticket_id">
        <option v-for="t in releasableTickets" :key="t.id" :value="t.id">{{ t.ticket_code }} · 闸代{{ t.generation }}</option>
      </select>
    </div>
    <div><label>值班员</label><input v-model="gateForm.officer"/></div>
  </div>
  <div class="actions">
    <button @click="releaseGate" :disabled="!releasableTickets.length">确认放行</button>
    <button class="secondary" @click="refresh">刷新</button>
  </div>
  <table class="data-table">
    <thead><tr><th>放行号</th><th>票号</th><th>车道</th><th>值班员</th><th>时间</th><th>最新闸代快照</th></tr></thead>
    <tbody>
      <tr v-for="g in gateReleases" :key="g.id">
        <td>{{ g.release_ref }}</td>
        <td>{{ g.ticket_code }}</td>
        <td>{{ g.lane_code }}</td>
        <td>{{ g.officer }}</td>
        <td>{{ g.released_at }}</td>
        <td>
          <span class="badge" :class="(g.has_latest_snapshot === 1 || g.has_latest_snapshot === true) ? 'pass' : 'fail'">
            {{ (g.has_latest_snapshot === 1 || g.has_latest_snapshot === true) ? '齐套' : '缺快照' }}
          </span>
        </td>
      </tr>
    </tbody>
  </table>
</section>
`;
