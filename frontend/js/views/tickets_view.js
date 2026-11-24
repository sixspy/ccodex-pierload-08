export const ticketsViewTemplate = `
<section class="panel">
  <h2>过磅票采集</h2>
  <p class="hint">录入各轴重 JSON；超重自动旁路挂起并开超重记录。放行齐套状态与放行/快照/对账/总览同源（就闸口库表）。</p>
  <div class="form-row">
    <div><label>车道</label>
      <select v-model.number="ticketForm.lane_id">
        <option v-for="l in lanes" :key="l.id" :value="l.id">{{ l.lane_code }}</option>
      </select>
    </div>
    <div><label>提单号</label>
      <select v-model="ticketForm.bl_ref">
        <option v-for="b in blList" :key="b.bl_code" :value="b.bl_code">{{ b.bl_code }}</option>
      </select>
    </div>
    <div><label>车牌</label><input v-model="ticketForm.vehicle_plate"/></div>
    <div><label>票号(可空)</label><input v-model="ticketForm.ticket_code"/></div>
  </div>
  <label>轴重 JSON</label>
  <textarea v-model="ticketForm.axles_json" rows="4" placeholder='[{"axle":1,"w":8.2}]'></textarea>
  <div class="actions">
    <button @click="createTicket">过磅入闸</button>
    <button class="secondary" @click="refresh">刷新</button>
  </div>
  <table class="data-table">
    <thead><tr><th>票号</th><th>车道</th><th>提单</th><th>毛重</th><th>状态</th><th>代</th><th>闸口齐套</th><th></th></tr></thead>
    <tbody>
      <tr v-for="t in tickets" :key="t.id" @click="selectTicket(t)">
        <td>{{ t.ticket_code }}</td>
        <td>{{ t.lane_code }}</td>
        <td>{{ t.bl_ref }}</td>
        <td>{{ fmtT(t.gross_t) }}</td>
        <td><span class="badge" :class="ticketClass(t.status)">{{ t.status }}</span></td>
        <td>{{ t.generation }}</td>
        <td>
          <span v-if="releaseSnapshotMap[t.id] === true" class="badge pass">已放行齐套</span>
          <span v-else-if="t.status === '已放行'" class="badge fail">放行缺快照</span>
          <span v-else-if="t.status === '已封闸'" class="badge warn">已封闸待放行</span>
          <span v-else class="badge muted">未封闸</span>
        </td>
        <td><button class="mini-btn" @click.stop="loadTicketDetail(t.id)">详情</button></td>
      </tr>
    </tbody>
  </table>
  <div v-if="ticketDetail" class="detail-box">
    <p>车牌 {{ ticketDetail.ticket.vehicle_plate }} · 超重挂起 {{ ticketDetail.overload_holds.length }} 条</p>
    <p>最新闸代快照 {{ ticketDetail.has_latest_snapshot ? '在' : '缺' }} · 已放行 {{ ticketDetail.released ? '是' : '否' }} · 放行齐套 {{ ticketDetail.release_snapshot_complete ? '是' : '否' }}</p>
  </div>
</section>
`;
