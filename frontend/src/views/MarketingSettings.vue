<template>
  <div class="marketing-settings">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>{{ ui.labels.marketing_settings }}</span>
          <el-button
            v-if="activeTab !== 'broadband'"
            type="success"
            :loading="saving"
            @click="saveRules"
          >保存行分类规则</el-button>
          <el-button
            v-else
            type="success"
            :loading="savingBroadband"
            @click="saveBroadbandRules"
          >保存宽带规则</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="按数据源分别配置行分类规则。线上直办、办理工单、降套维系共用原有行分类规则；宽带营销支持独立组织机构规则，并自动继承办理工单的组织机构规则，最后按工号兜底。"
        style="margin-bottom: 12px"
      />

      <el-tabs v-model="activeTab">
        <el-tab-pane label="线上直办" name="online">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="线上直办规则只接受“线上直办-*”和“降套维系”行分类；组织机构规则会同时继承到办理工单和宽带营销。"
            style="margin-bottom: 12px"
          />
          <el-form inline>
            <el-form-item>
              <el-button type="primary" @click="addOnlineRule">新增线上直办规则</el-button>
            </el-form-item>
            <el-form-item label="未分类产品行">
              <el-tag type="warning">{{ previews.xszb.unclassified }}</el-tag>
            </el-form-item>
          </el-form>

          <el-table :data="onlineRules" border stripe max-height="360">
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
            </el-table-column>
            <el-table-column label="归入行" min-width="170">
              <template #default="{ row }">
                <el-select v-model="row.row_label" filterable style="width: 100%">
                  <el-option v-for="label in ONLINE_ROW_LABELS" :key="label" :label="label" :value="label" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配字段" width="170">
              <template #default="{ row }">
                <el-select v-model="row.field" style="width: 100%">
                  <el-option v-for="item in OVERALL_FIELDS" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配方式" width="140">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配内容" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.pattern" :placeholder="patternPlaceholder(row)" />
                <div v-if="row.match_type === 'regex'" class="regex-hint">正则例：热线|营销</div>
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeOverallRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left">线上直办组织机构命中预览</el-divider>
          <el-table :data="onlineOrganizations" border stripe max-height="320">
            <el-table-column prop="org_name" label="组织机构" min-width="420" show-overflow-tooltip />
            <el-table-column prop="count" label="明细行数" width="100" />
            <el-table-column prop="row_label" label="命中行分类" width="160" />
          </el-table>

          <el-divider content-position="left">线上直办未分类取值预览</el-divider>
          <el-table :data="previews.xszb.samples" border stripe max-height="300">
            <el-table-column prop="field" label="字段" width="180" />
            <el-table-column prop="value" label="取值" min-width="360" show-overflow-tooltip />
            <el-table-column prop="count" label="行数" width="90" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="办理工单" name="work_order">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="办理工单先按组织机构规则匹配，未命中再按建单租户规则兜底。线上直办的组织机构规则会自动继承到办理工单和宽带营销。"
            style="margin-bottom: 12px"
          />
          <el-form inline>
            <el-form-item>
              <el-button type="primary" @click="addWorkOrderOrgRule">新增组织机构规则</el-button>
              <el-button type="primary" @click="addWorkOrderTenantRule">新增租户规则</el-button>
            </el-form-item>
            <el-form-item label="未分类工单行">
              <el-tag type="warning">{{ previews.fwgd.unclassified }}</el-tag>
            </el-form-item>
          </el-form>

          <div class="section-title">组织机构规则（优先）</div>
          <el-table :data="workOrderOrgRules" border stripe max-height="300">
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
            </el-table-column>
            <el-table-column label="归入行" min-width="170">
              <template #default="{ row }">
                <el-select v-model="row.row_label" filterable style="width: 100%">
                  <el-option v-for="label in MARKETING_ROW_LABELS" :key="label" :label="label" :value="label" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配方式" width="140">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配内容" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.pattern" :placeholder="patternPlaceholder(row)" />
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeOverallRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="section-title">继承自线上直办的组织机构规则（只读）</div>
          <el-alert
            v-if="!inheritedOnlineOrgRules.length"
            type="info"
            :closable="false"
            show-icon
            title="暂无继承规则。线上直办中字段为“组织机构”的规则会自动用于办理工单。"
          />
          <el-table v-else :data="inheritedOnlineOrgRules" border stripe max-height="260">
            <el-table-column label="来源" width="130">
              <template #default="{ row }"><el-tag size="small">{{ row.source }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="source_row_label" label="原归入行" min-width="160" />
            <el-table-column prop="row_label" label="办理工单归入行" min-width="160" />
            <el-table-column prop="match_type" label="匹配方式" width="120" />
            <el-table-column prop="pattern" label="匹配内容" min-width="220" show-overflow-tooltip />
            <el-table-column prop="priority" label="优先级" width="90" />
          </el-table>

          <div class="section-title">建单租户规则（兜底）</div>
          <el-table :data="workOrderTenantRules" border stripe max-height="260">
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
            </el-table-column>
            <el-table-column label="归入行" min-width="170">
              <template #default="{ row }">
                <el-select v-model="row.row_label" filterable style="width: 100%">
                  <el-option v-for="label in MARKETING_ROW_LABELS" :key="label" :label="label" :value="label" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配方式" width="140">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="建单租户" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.pattern" :placeholder="patternPlaceholder(row)" />
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeOverallRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left">办理工单组织机构命中预览</el-divider>
          <el-table :data="workOrderOrganizations" border stripe max-height="320">
            <el-table-column prop="org_name" label="组织机构/建单租户" min-width="420" show-overflow-tooltip />
            <el-table-column prop="count" label="明细行数" width="100" />
            <el-table-column prop="row_label" label="命中行分类" width="160" />
          </el-table>

          <el-divider content-position="left">办理工单未分类取值预览</el-divider>
          <el-table :data="previews.fwgd.samples" border stripe max-height="300">
            <el-table-column prop="field" label="字段" width="180" />
            <el-table-column prop="value" label="取值" min-width="360" show-overflow-tooltip />
            <el-table-column prop="count" label="行数" width="90" />
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="宽带营销" name="broadband">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="宽带营销分类顺序：独立组织机构规则 → 继承的办理工单组织机构规则 → 工号兜底规则。工号规则用于 --、QYY 等匹配不到组织机构的情况。"
            style="margin-bottom: 12px"
          />

          <div class="section-title">继承的组织机构规则（只读）</div>
          <el-alert
            v-if="!broadbandRules.inherited_org_rules.length"
            type="info"
            :closable="false"
            show-icon
            title="暂无继承规则。请在“线上直办”或“办理工单”中配置字段为“组织机构”的规则。"
          />
          <el-table v-else :data="broadbandRules.inherited_org_rules" border stripe max-height="280">
            <el-table-column label="来源" width="130">
              <template #default="{ row }"><el-tag size="small">{{ row.source }}</el-tag></template>
            </el-table-column>
            <el-table-column prop="source_row_label" label="原归入行" min-width="160" />
            <el-table-column prop="row_label" label="宽带归入行" min-width="160" />
            <el-table-column prop="match_type" label="匹配方式" width="120" />
            <el-table-column prop="pattern" label="匹配内容" min-width="220" show-overflow-tooltip />
            <el-table-column prop="priority" label="优先级" width="90" />
          </el-table>

          <div class="section-title">宽带独立组织机构规则（优先于继承规则）</div>
          <el-form inline>
            <el-form-item>
              <el-button type="primary" @click="addBroadbandOrgRule">新增独立组织机构规则</el-button>
            </el-form-item>
          </el-form>
          <el-table :data="broadbandRules.org_rules" border stripe max-height="280">
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
            </el-table-column>
            <el-table-column label="归入行" min-width="170">
              <template #default="{ row }">
                <el-select v-model="row.row_label" filterable style="width: 100%">
                  <el-option v-for="label in MARKETING_ROW_LABELS" :key="label" :label="label" :value="label" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配方式" width="140">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="组织机构" min-width="220">
              <template #default="{ row }"><el-input v-model="row.pattern" placeholder="如：热线运营组" /></template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeBroadbandOrgRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <div class="section-title">工号兜底规则（组织机构分类失败后生效）</div>
          <el-form inline>
            <el-form-item>
              <el-button type="primary" @click="addBroadbandEmpRule">新增工号规则</el-button>
            </el-form-item>
            <el-form-item label="未分类宽带订单">
              <el-tag type="warning">{{ broadbandPreview.unclassified }}</el-tag>
            </el-form-item>
            <el-form-item label="工号未匹配组织机构">
              <el-tag type="info">{{ broadbandPreview.no_org }}</el-tag>
            </el-form-item>
          </el-form>
          <el-table :data="broadbandRules.emp_rules" border stripe max-height="280">
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
            </el-table-column>
            <el-table-column label="归入行" min-width="170">
              <template #default="{ row }">
                <el-select v-model="row.row_label" filterable style="width: 100%">
                  <el-option v-for="label in MARKETING_ROW_LABELS" :key="label" :label="label" :value="label" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配方式" width="140">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in EMP_MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="下单新客服工号" min-width="220">
              <template #default="{ row }"><el-input v-model="row.pattern" placeholder="如：--、QYY" /></template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeBroadbandEmpRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>

          <el-divider content-position="left">未分类宽带订单预览</el-divider>
          <el-table :data="broadbandPreview.samples" border stripe max-height="320">
            <el-table-column prop="emp_no" label="下单新客服工号" min-width="180">
              <template #default="{ row }">{{ row.emp_no || '（空工号）' }}</template>
            </el-table-column>
            <el-table-column prop="org_name" label="匹配到的组织机构" min-width="360">
              <template #default="{ row }">{{ row.org_name || '未匹配组织机构' }}</template>
            </el-table-column>
            <el-table-column prop="count" label="订单数" width="90" />
            <el-table-column label="操作" width="150" align="center">
              <template #default="{ row }">
                <el-button
                  type="primary"
                  link
                  :disabled="!row.emp_no"
                  @click="addEmpRuleFromSample(row)"
                >添加工号规则</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>

        <el-tab-pane label="降套维系" name="downgrade">
          <el-alert
            type="info"
            :closable="false"
            show-icon
            title="降套维系列只使用线上直办数据，行分类固定为“降套维系”。"
            style="margin-bottom: 12px"
          />
          <el-form inline>
            <el-form-item>
              <el-button type="primary" @click="addDowngradeRule">新增降套维系规则</el-button>
            </el-form-item>
          </el-form>
          <el-table :data="downgradeRules" border stripe max-height="360">
            <el-table-column label="启用" width="70" align="center">
              <template #default="{ row }"><el-switch v-model="row.enabled" size="small" /></template>
            </el-table-column>
            <el-table-column label="归入行" width="160">
              <template #default><span>降套维系</span></template>
            </el-table-column>
            <el-table-column label="匹配字段" width="170">
              <template #default="{ row }">
                <el-select v-model="row.field" style="width: 100%">
                  <el-option v-for="item in OVERALL_FIELDS" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配方式" width="140">
              <template #default="{ row }">
                <el-select v-model="row.match_type" style="width: 100%">
                  <el-option v-for="item in MATCH_TYPES" :key="item.value" :label="item.label" :value="item.value" />
                </el-select>
              </template>
            </el-table-column>
            <el-table-column label="匹配内容" min-width="220">
              <template #default="{ row }">
                <el-input v-model="row.pattern" :placeholder="patternPlaceholder(row)" />
              </template>
            </el-table-column>
            <el-table-column label="优先级" width="110">
              <template #default="{ row }"><el-input-number v-model="row.priority" :min="0" :max="9999" size="small" /></template>
            </el-table-column>
            <el-table-column label="操作" width="80" align="center">
              <template #default="{ row }">
                <el-button type="danger" link @click="removeOverallRule(row)">删除</el-button>
              </template>
            </el-table-column>
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-card class="key-product-card">
      <template #header>
        <div class="card-header">
          <span>重点业务产品设置</span>
          <el-button type="success" :loading="savingProducts" @click="saveKeyProducts">保存重点业务产品</el-button>
        </div>
      </template>

      <el-alert
        type="info"
        :closable="false"
        show-icon
        title="配置后，总体营销页下方将按这里的业务名和排序展示产品统计列；可通过产品ID、产品名称或产品库下拉框添加。"
        style="margin-bottom: 12px"
      />

      <el-form inline class="key-product-toolbar">
        <el-form-item label="从产品库添加">
          <el-select
            v-model="selectedProduct"
            filterable
            remote
            clearable
            :remote-method="searchProducts"
            :loading="productOptionsLoading"
            placeholder="搜索产品ID或产品名称"
            style="width: 360px"
            @change="addProductFromOptions"
          >
            <el-option
              v-for="item in productOptions"
              :key="productOptionKey(item)"
              :label="productOptionLabel(item)"
              :value="productOptionKey(item)"
            />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button @click="addEmptyProduct">手动新增</el-button>
        </el-form-item>
      </el-form>

      <el-table :data="keyProducts" border stripe max-height="360">
        <el-table-column label="排序" width="150" align="center">
          <template #default="{ $index }">
            <span class="sort-index">{{ $index + 1 }}</span>
            <el-button link type="primary" :disabled="$index === 0" @click="moveProduct($index, -1)">上移</el-button>
            <el-button link type="primary" :disabled="$index === keyProducts.length - 1" @click="moveProduct($index, 1)">下移</el-button>
          </template>
        </el-table-column>
        <el-table-column label="业务名" min-width="180">
          <template #default="{ row }">
            <el-input v-model="row.business_name" placeholder="用于表格列名" />
          </template>
        </el-table-column>
        <el-table-column label="产品ID" width="180">
          <template #default="{ row }">
            <el-input v-model="row.product_id" placeholder="产品ID" />
          </template>
        </el-table-column>
        <el-table-column label="产品名称" min-width="260">
          <template #default="{ row }">
            <el-input v-model="row.product_name" placeholder="产品名称" />
          </template>
        </el-table-column>
        <el-table-column label="操作" width="80" align="center">
          <template #default="{ $index }">
            <el-button type="danger" link @click="keyProducts.splice($index, 1)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { api } from '../stores/user'
import { useUiConfigStore } from '../stores/uiConfig'
import { ElMessage } from 'element-plus'

const ui = useUiConfigStore()
const activeTab = ref('online')
const saving = ref(false)
const savingBroadband = ref(false)
const config = reactive({ rules: [] })
const broadbandRules = reactive({ org_rules: [], emp_rules: [], inherited_org_rules: [] })
const organizations = ref([])
const previews = reactive({
  xszb: { unclassified: 0, samples: [] },
  fwgd: { unclassified: 0, samples: [] }
})
const broadbandPreview = reactive({ unclassified: 0, no_org: 0, samples: [] })
const keyProducts = ref([])
const productOptions = ref([])
const selectedProduct = ref('')
const productOptionsLoading = ref(false)
const savingProducts = ref(false)

const MATCH_TYPES = [
  { value: 'contains', label: '包含' },
  { value: 'equals', label: '等于' },
  { value: 'prefix', label: '前缀' },
  { value: 'suffix', label: '后缀' },
  { value: 'regex', label: '正则（表达式）' }
]

const EMP_MATCH_TYPES = [
  { value: 'equals', label: '等于' },
  { value: 'prefix', label: '前缀' },
  { value: 'regex', label: '正则（表达式）' }
]

const ONLINE_ROW_LABELS = [
  '线上直办-热线', '线上直办-区域', '线上直办-维系', '线上直办-工单', '线上直办-分公司'
]

const MARKETING_ROW_LABELS = [
  '营销工单-热线', '营销工单-区域', '营销工单-维系', '营销工单-工单', '营销工单-分公司'
]

const OVERALL_FIELDS = [
  { value: 'org_name', label: '组织机构' },
  { value: 'tenant', label: '建单租户' },
  { value: 'channel', label: '受理渠道' },
  { value: 'pos_sequence', label: '人员岗位性质' },
  { value: 'develop_depart_name', label: '发展渠道' },
  { value: 'service_type', label: '重点业务分类' },
  { value: 'data_type', label: '数据类型' },
  { value: 'area_name', label: '地市' },
  { value: 'tb_region_name', label: '通报区域' }
]

function isOrgRule(rule) {
  return (rule.field || 'org_name') === 'org_name'
}

const onlineRules = computed(() => config.rules.filter((rule) => ONLINE_ROW_LABELS.includes(rule.row_label)))
const downgradeRules = computed(() => config.rules.filter((rule) => rule.row_label === '降套维系'))
const workOrderOrgRules = computed(() => config.rules.filter(
  (rule) => MARKETING_ROW_LABELS.includes(rule.row_label) && isOrgRule(rule)
))
const workOrderTenantRules = computed(() => config.rules.filter(
  (rule) => MARKETING_ROW_LABELS.includes(rule.row_label) && rule.field === 'tenant'
))
const inheritedOnlineOrgRules = computed(() => onlineRules.value
  .filter((rule) => rule.enabled !== false && isOrgRule(rule))
  .map((rule) => ({
    ...rule,
    source: '线上直办规则',
    source_row_label: rule.row_label,
    row_label: rule.row_label.replace('线上直办-', '营销工单-')
  })))
const onlineOrganizations = computed(() => organizations.value.filter((item) => item.data_type === 'xszb'))
const workOrderOrganizations = computed(() => organizations.value.filter((item) => item.data_type === 'fwgd'))

function patternPlaceholder(row) {
  return row.match_type === 'regex' ? '正则表达式，如：热线|营销' : '如：热线运营组'
}

function newOverallRule(rowLabel, field = 'org_name') {
  return {
    id: '',
    row_label: rowLabel,
    field,
    match_type: 'contains',
    pattern: '',
    priority: 10,
    enabled: true
  }
}

function addOnlineRule() {
  config.rules.push(newOverallRule('线上直办-热线'))
}

function addDowngradeRule() {
  config.rules.push(newOverallRule('降套维系'))
}

function addWorkOrderOrgRule() {
  config.rules.push(newOverallRule('营销工单-热线', 'org_name'))
}

function addWorkOrderTenantRule() {
  config.rules.push(newOverallRule('营销工单-热线', 'tenant'))
}

function removeOverallRule(row) {
  const index = config.rules.indexOf(row)
  if (index >= 0) config.rules.splice(index, 1)
}

function addBroadbandOrgRule() {
  broadbandRules.org_rules.push(newOverallRule('营销工单-热线', 'org_name'))
}

function removeBroadbandOrgRule(row) {
  const index = broadbandRules.org_rules.indexOf(row)
  if (index >= 0) broadbandRules.org_rules.splice(index, 1)
}

function addBroadbandEmpRule() {
  broadbandRules.emp_rules.push({
    id: '',
    row_label: '营销工单-热线',
    match_type: 'equals',
    pattern: '',
    priority: 10,
    enabled: true
  })
}

function removeBroadbandEmpRule(row) {
  const index = broadbandRules.emp_rules.indexOf(row)
  if (index >= 0) broadbandRules.emp_rules.splice(index, 1)
}

function addEmpRuleFromSample(sample) {
  if (!sample?.emp_no) return
  const pattern = sample.emp_no
  broadbandRules.emp_rules.push({
    id: '',
    row_label: '营销工单-热线',
    match_type: /^[A-Za-z]+$/.test(pattern) ? 'prefix' : 'equals',
    pattern,
    priority: 10,
    enabled: true
  })
  ElMessage.success(`已添加工号规则：${sample.emp_no}`)
}

async function loadRules() {
  const res = await api.get('/marketing/overall-row-rules')
  config.rules = res.data.rules || []
}

async function loadBroadbandRules() {
  const res = await api.get('/marketing/broadband-rules')
  broadbandRules.org_rules = res.data.org_rules || []
  broadbandRules.emp_rules = res.data.emp_rules || []
  broadbandRules.inherited_org_rules = res.data.inherited_org_rules || []
}

async function loadPreviews() {
  try {
    const [orgRes, xszbRes, fwgdRes] = await Promise.all([
      api.get('/marketing/organizations'),
      api.get('/marketing/row-rule-preview', { params: { source: 'xszb' } }),
      api.get('/marketing/row-rule-preview', { params: { source: 'fwgd' } })
    ])
    organizations.value = orgRes.data.items || []
    previews.xszb.unclassified = xszbRes.data.unclassified || 0
    previews.xszb.samples = xszbRes.data.samples || []
    previews.fwgd.unclassified = fwgdRes.data.unclassified || 0
    previews.fwgd.samples = fwgdRes.data.samples || []
  } catch (e) {
    /* 预览失败不影响规则编辑 */
  }
}

async function loadBroadbandPreview() {
  try {
    const res = await api.get('/marketing/broadband-rule-preview')
    broadbandPreview.unclassified = res.data.unclassified || 0
    broadbandPreview.no_org = res.data.no_org || 0
    broadbandPreview.samples = res.data.samples || []
  } catch (e) {
    /* 预览失败不影响规则编辑 */
  }
}

async function saveRules() {
  saving.value = true
  try {
    await api.put('/marketing/overall-row-rules', { rules: config.rules })
    ElMessage.success('总体营销行分类规则已保存')
    await Promise.all([loadRules(), loadPreviews(), loadBroadbandRules(), loadBroadbandPreview()])
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    saving.value = false
  }
}

async function saveBroadbandRules() {
  savingBroadband.value = true
  try {
    await api.put('/marketing/broadband-rules', {
      org_rules: broadbandRules.org_rules,
      emp_rules: broadbandRules.emp_rules
    })
    ElMessage.success('宽带营销规则已保存')
    await Promise.all([loadBroadbandRules(), loadBroadbandPreview()])
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingBroadband.value = false
  }
}

function productOptionKey(item) {
  return `${item.product_id || ''}\u0001${item.product_name || ''}`
}

function productOptionLabel(item) {
  const count = item.count ? `，明细 ${item.count} 条` : ''
  if (item.product_id && item.product_name) return `${item.product_name}（${item.product_id}${count}）`
  return `${item.product_name || item.product_id}${count}`
}

async function loadKeyProducts() {
  const res = await api.get('/marketing/key-products')
  keyProducts.value = (res.data.products || []).map((item) => ({
    id: item.id || '',
    business_name: item.business_name || '',
    product_id: item.product_id || '',
    product_name: item.product_name || '',
  }))
}

async function loadProductOptions(keyword = '') {
  productOptionsLoading.value = true
  try {
    const res = await api.get('/marketing/product-options', { params: keyword ? { keyword } : {} })
    productOptions.value = res.data.items || []
  } catch (e) {
    productOptions.value = []
  } finally {
    productOptionsLoading.value = false
  }
}

function searchProducts(keyword) {
  loadProductOptions(keyword)
}

function addProductFromOptions(value) {
  if (!value) return
  const item = productOptions.value.find((option) => productOptionKey(option) === value)
  if (!item) return
  keyProducts.value.push({
    id: '',
    business_name: item.product_name || item.product_id,
    product_id: item.product_id || '',
    product_name: item.product_name || '',
  })
  selectedProduct.value = ''
}

function addEmptyProduct() {
  keyProducts.value.push({ id: '', business_name: '', product_id: '', product_name: '' })
}

function moveProduct(index, offset) {
  const target = index + offset
  if (target < 0 || target >= keyProducts.value.length) return
  const [item] = keyProducts.value.splice(index, 1)
  keyProducts.value.splice(target, 0, item)
}

async function saveKeyProducts() {
  savingProducts.value = true
  try {
    await api.put('/marketing/key-products', {
      products: keyProducts.value.map((item, index) => ({
        id: item.id || null,
        business_name: (item.business_name || '').trim(),
        product_id: (item.product_id || '').trim(),
        product_name: (item.product_name || '').trim(),
        sort: index
      }))
    })
    ElMessage.success('重点业务产品设置已保存')
    await loadKeyProducts()
    await loadProductOptions()
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    savingProducts.value = false
  }
}

onMounted(async () => {
  try {
    await loadRules()
    await Promise.all([
      loadPreviews(),
      loadBroadbandRules(),
      loadBroadbandPreview(),
      loadKeyProducts(),
      loadProductOptions()
    ])
  } catch (e) {
    ElMessage.error(e.response?.data?.detail || '加载失败')
  }
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.regex-hint {
  margin-top: 2px;
  color: #909399;
  font-size: 12px;
  line-height: 1.4;
}
.section-title {
  margin: 18px 0 10px;
  font-weight: 600;
  color: #303133;
}
.key-product-card {
  margin-top: 16px;
}
.key-product-toolbar {
  margin-bottom: 4px;
}
.sort-index {
  display: inline-block;
  min-width: 24px;
  color: #606266;
}
</style>
