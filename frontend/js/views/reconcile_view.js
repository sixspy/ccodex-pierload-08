export const reconcileViewTemplate = `
<section class="grid-2">
  <section class="panel">
    <h2>提单对账</h2>
    <p class="hint">毛重比对就提单册；放行齐套口径就闸口（正式放行须配最新闸代快照），两口径不混用。</p>
    <div class="form-row">
      <div><label>提单号</label><input v-model="reconCode"/></div>
    </div>
    <div class="actions">
      <button @click="loadReconcile">对账</button>
      <button class="secondary" @click="loadAllReconcile">全量</button>
    </div>
    <div v-if="reconOne" class="detail-box">
      <p>申报 {{ reconOne.declared_gross_t }}t · 过磅合计 {{ reconOne.ticket_sum_t }}t</p>
      <p :class="reconOne.balanced ? 'ok' : 'bad'">{{ reconOne.balanced ? '账实平衡' : '偏差待查' }}</p>
      <p>正式放行 {{ reconOne.released_count ?? 0 }} 笔 · 快照齐套 {{ reconOne.snapshot_complete_releases ?? 0 }} 笔 · 缺快照 {{ reconOne.releases_missing_snapshot ?? 0 }} 笔</p>
      <p :class="(reconOne.releases_missing_snapshot ?? 0) > 0 ? 'bad' : (reconOne.proof_ready ? 'ok' : 'muted')">
        {{ reconOne.proof_ready ? '可出证明（闸口齐套）' : ((reconOne.releases_missing_snapshot ?? 0) > 0 ? '无快照禁放：存在缺快照正式行，不得判齐套' : '未齐套') }}
      </p>
    </div>
    <ul v-if="reconAllItems.length">
      <li v-for="r in reconAllItems" :key="r.bl_code">
        {{ r.bl_code }} · {{ r.balanced ? '平' : '偏' }} · 缺快照 {{ r.releases_missing_snapshot ?? 0 }}
      </li>
    </ul>
  </section>
  <section class="panel">
    <h2>单票证明</h2>
    <div class="form-row"><div><label>票号</label><input v-model="proofCode"/></div></div>
    <div class="actions"><button @click="loadProof">拉证明</button></div>
    <div v-if="proofOne" class="detail-box">
      <p>提单匹配 {{ proofOne.manifest_matches_bl ? '是' : '否' }}</p>
      <p>超重闭环 {{ proofOne.overload_closed ? '是' : '否' }}</p>
      <p>最新闸代快照 <span :class="proofOne.has_latest_snapshot ? 'ok' : 'bad'">{{ proofOne.has_latest_snapshot ? '在' : '缺' }}</span></p>
      <p>已放行 {{ proofOne.released ? '是' : '否' }}</p>
      <p :class="proofOne.coherent ? 'ok' : 'bad'">一致（齐套） {{ proofOne.coherent ? '是' : '否' }}</p>
    </div>
  </section>
</section>
`;
