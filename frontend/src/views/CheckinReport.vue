<template>
  <div class="checkin-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>签入签出报表</span>
          <el-button v-if="userStore.hasPermission('checkin_report.export')" type="success" size="small" @click="handleExport">导出</el-button>
        </div>
      </template>

      <el-form inline>
        <el-form-item label="查询方式">
          <el-radio-group v-model="searchForm.type" @change="handleTypeChange">
            <el-radio value="day">按天</el-radio>
            <el-radio value="month">按月</el-radio>
            <el-radio value="range">自定义</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>

      <el-form inline>
        <el-form-item v-if="searchForm.type === 'day'" label="日期">
          <el-date-picker v-model="searchForm.date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'month'" label="月份">
          <el-date-picker v-model="searchForm.month" type="month" value-format="YYYY-MM" placeholder="选择月份" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="开始日期">
          <el-date-picker v-model="searchForm.start_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item v-if="searchForm.type === 'range'" label="结束日期">
          <el-date-picker v-model="searchForm.end_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="姓名">
          <el-input v-model="searchForm.name" placeholder="请输入姓名" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="工号">
          <el-input v-model="searchForm.emp_no" placeholder="请输入工号" clearable style="width: 120px" />
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="searchForm.team" placeholder="全部班组" clearable filterable style="width: 140px">
            <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
          </el-select>
        </el-form-item>
        <el-form-item>
          <el-button type="primary" @click="loadData">查询</el-button>
        </el-form-item>
      </el-form>

      <el-row :gutter="20" class="stats-row">
        <el-col :span="4">
          <el-statistic title="签入人次" :value="stats.total_checkins" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="总人数" :value="stats.emp_count" />
        </el-col>
        <el-col :span="4">
          <el-statistic title="总时长" :value="stats.total_hours" :precision="1">
            <template #suffix>小时</template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic title="平均时长" :value="stats.avg_hours" :precision="1">
            <template #suffix>小时</template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic title="超时人数" :value="stats.overtime_count">
            <template #suffix>
              <el-tooltip v-if="stats.overtime_count > 0" :content="overtimeNames.join(', ')" placement="top">
                <el-button type="warning" link @click="toggleFilter('overtime')">
                  {{ filterType === 'overtime' ? '已筛选' : '点击筛选' }}
                </el-button>
              </el-tooltip>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="4">
          <el-statistic title="过短人数" :value="stats.undertime_count">
            <template #suffix>
              <el-tooltip v-if="stats.undertime_count > 0" :content="undertimeNames.join(', ')" placement="top">
                <el-button type="warning" link @click="toggleFilter('undertime')">
                  {{ filterType === 'undertime' ? '已筛选' : '点击筛选' }}
                </el-button>
              </el-tooltip>
            </template>
          </el-statistic>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center">
              <span style="font-size: 14px; color: #606266">员工工时排名（点击员工筛选）</span>
              <el-radio-group v-model="chartType" size="small">
                <el-radio-button value="bar">柱状图</el-radio-button>
                <el-radio-button value="line">折线图</el-radio-button>
              </el-radio-group>
            </div>
            <Echart :options="hoursChartOptions" height="280px" @click="handleHoursChartClick" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; font-size: 14px; color: #606266">员工签入次数排名（点击员工筛选）</div>
            <Echart :options="checkinCountOptions" height="300px" @click="handleCheckinChartClick" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 20px">
        <el-col :span="24">
          <el-card shadow="hover">
            <div style="margin-bottom: 10px; font-size: 14px; color: #606266">班组工时分布（点击班组筛选）</div>
            <Echart :options="deptHoursOptions" height="300px" @click="handleTeamChartClick" />
          </el-card>
        </el-col>
      </el-row>

      <el-table :data="paginatedData" border stripe show-summary max-height="calc(100vh - 350px)">
        <ColumnWithTip prop="emp_no" label="账号" width="100" :annotation="checkinAnnMap['emp_no']" />
        <ColumnWithTip prop="name" label="用户名" width="100" :annotation="checkinAnnMap['name']" />
        <ColumnWithTip prop="dept" label="所属部门" min-width="150" :annotation="checkinAnnMap['dept']" />
        <ColumnWithTip prop="team" label="班组" width="100" :annotation="checkinAnnMap['team']" />
        <ColumnWithTip prop="checkin_count" label="签入次数" width="80" sortable :annotation="checkinAnnMap['checkin_count']" />
        <ColumnWithTip prop="total_hours" label="工作时长" width="80" sortable :annotation="checkinAnnMap['total_hours']">
          <template #default="{ row }">
            {{ row.total_hours.toFixed(1) }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="hour_status_text" label="工时状态" width="120" :annotation="checkinAnnMap['hour_status_text']">
          <template #default="{ row }">
            <el-tag v-if="row.hour_status === 'overtime'" type="danger" size="small">超时</el-tag>
            <el-tag v-else-if="row.hour_status === 'undertime'" type="warning" size="small">过短</el-tag>
            <el-tag v-else-if="row.hour_status === 'normal'" type="success" size="small">正常</el-tag>
            <span v-else>-</span>
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="avg_punctuality_rate" label="遵时率" width="80" sortable :annotation="checkinAnnMap['avg_punctuality_rate']">
          <template #default="{ row }">
            {{ row.avg_punctuality_rate != null ? row.avg_punctuality_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="total_call_duration" label="通话时长" width="80" sortable :annotation="checkinAnnMap['total_call_duration']">
          <template #default="{ row }">
            {{ row.total_call_duration != null ? row.total_call_duration.toFixed(1) + 'h' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="total_organize_duration" label="整理时长" width="80" sortable :annotation="checkinAnnMap['total_organize_duration']">
          <template #default="{ row }">
            {{ row.total_organize_duration != null ? row.total_organize_duration.toFixed(1) + 'h' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="avg_utilization_rate" label="工时利用率" width="90" sortable :annotation="checkinAnnMap['avg_utilization_rate']">
          <template #default="{ row }">
            {{ row.avg_utilization_rate != null ? row.avg_utilization_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="avg_attendance_rate" label="班表出勤率" width="90" sortable :annotation="checkinAnnMap['avg_attendance_rate']">
          <template #default="{ row }">
            {{ row.avg_attendance_rate != null ? row.avg_attendance_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="training_minutes" label="培训扣除(分)" width="90" sortable :annotation="checkinAnnMap['training_minutes']">
          <template #default="{ row }">
            {{ row.training_minutes != null ? row.training_minutes : 0 }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip prop="computed_punctuality_rate" label="系统遵时率" width="90" sortable :annotation="checkinAnnMap['computed_punctuality_rate']">
          <template #default="{ row }">
            {{ row.computed_punctuality_rate != null ? row.computed_punctuality_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <el-table-column label="签入明细" min-width="350">
          <template #default="{ row }">
            <template v-if="row.checkins && row.checkins.length">
              <div v-for="(c, idx) in row.checkins" :key="idx" style="display: inline-block; margin: 2px 8px 2px 0;">
                <el-tag size="small">{{ idx + 1 }}: {{ c.checkin_time || '-' }} → {{ c.checkout_time || '-' }}</el-tag>
                <span style="margin-left: 4px; font-size: 12px; color: #666;">
                  ({{ c.duration.toFixed(1) }}h)
                </span>
              </div>
            </template>
            <span v-else>-</span>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="60" fixed="right">
          <template #default="{ row }">
            <el-button type="primary" link size="small" @click="openDetail(row)">详情</el-button>
          </template>
        </el-table-column>
      </el-table>

      <el-pagination
        v-if="tableData.length > 0"
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="[10, 20, 50, 100]"
        :total="tableData.length"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 15px; justify-content: flex-end"
      />
    </el-card>

    <el-drawer v-model="drawerVisible" :title="drawerTitle" size="70%" direction="rtl">
      <template v-if="personalDetail">
        <el-descriptions :column="2" border size="small" style="margin-bottom: 16px">
          <el-descriptions-item label="工号">{{ personalDetail.emp_info.emp_no }}</el-descriptions-item>
          <el-descriptions-item label="姓名">{{ personalDetail.emp_info.name }}</el-descriptions-item>
          <el-descriptions-item label="班组">{{ personalDetail.emp_info.team }}</el-descriptions-item>
          <el-descriptions-item label="部门">{{ personalDetail.emp_info.dept }}</el-descriptions-item>
        </el-descriptions>

        <el-row :gutter="12" class="stats-row">
          <el-col :span="3">
            <el-statistic :precision="1">
              <template #title>
                <span>排班总工时 <template v-if="summaryTip('total_scheduled_hours')"><el-tooltip :content="summaryContent('total_scheduled_hours')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.total_scheduled_hours }}</template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1">
              <template #title>
                <span>累计工时 <template v-if="summaryTip('total_hours')"><el-tooltip :content="summaryContent('total_hours')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.total_hours }}</template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1">
              <template #title>
                <span>班组平均工时 <template v-if="summaryTip('team_avg_hours')"><el-tooltip :content="summaryContent('team_avg_hours')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.team_avg_hours }}</template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="4">
            <div class="stat-custom">
              <div class="stat-label">
                <span>出勤/排班 <template v-if="summaryTip('attend_days')"><el-tooltip :content="summaryContent('attend_days')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </div>
              <div class="stat-value">
                <span class="stat-number">{{ personalDetail.summary.attend_days }}</span>
                <span class="stat-sub">/{{ personalDetail.summary.scheduled_days }}天</span>
              </div>
            </div>
          </el-col>
          <el-col :span="3">
            <el-statistic>
              <template #title>
                <span>超长工时 <template v-if="summaryTip('long_hour_days')"><el-tooltip :content="summaryContent('long_hour_days')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ localLongHourDays }}</template>
              <template #suffix>天</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic>
              <template #title>
                <span>晚签天数 <template v-if="summaryTip('late_days')"><el-tooltip :content="summaryContent('late_days')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.late_days }}</template>
              <template #suffix>天</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic>
              <template #title>
                <span>提前签出天数 <template v-if="summaryTip('early_days')"><el-tooltip :content="summaryContent('early_days')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.early_days }}</template>
              <template #suffix>天</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1">
              <template #title>
                <span>通话总时长 <template v-if="summaryTip('total_call_duration')"><el-tooltip :content="summaryContent('total_call_duration')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.total_call_duration || 0 }}</template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1">
              <template #title>
                <span>整理总时长 <template v-if="summaryTip('total_organize_duration')"><el-tooltip :content="summaryContent('total_organize_duration')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.total_organize_duration || 0 }}</template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic>
              <template #title>
                <span>培训总时长 <template v-if="summaryTip('total_training_minutes')"><el-tooltip :content="summaryContent('total_training_minutes')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></template></span>
              </template>
              <template #default>{{ personalDetail.summary.total_training_minutes || 0 }}</template>
              <template #suffix>分</template>
            </el-statistic>
          </el-col>
        </el-row>

        <el-row :gutter="12" style="margin-bottom: 16px">
          <el-col :span="8">
            <el-tag type="primary" style="width: 100%; justify-content: center; padding: 8px 0; font-size: 14px">
              早班 {{ personalDetail.summary.morning_shift_days }} 天
            </el-tag>
          </el-col>
          <el-col :span="8">
            <el-tag type="warning" style="width: 100%; justify-content: center; padding: 8px 0; font-size: 14px">
              中班 {{ personalDetail.summary.mid_shift_days }} 天
            </el-tag>
          </el-col>
          <el-col :span="8">
            <el-tag type="info" style="width: 100%; justify-content: center; padding: 8px 0; font-size: 14px">
              晚班 {{ personalDetail.summary.night_shift_days }} 天
            </el-tag>
          </el-col>
        </el-row>

        <el-row :gutter="16" style="margin-bottom: 16px">
          <el-col :span="14">
            <el-card shadow="hover">
              <div style="margin-bottom: 8px; display: flex; align-items: center; gap: 8px; flex-wrap: nowrap">
                <span style="font-size: 14px; color: #606266; white-space: nowrap">每日工时趋势</span>
                <span style="font-size: 13px; color: #909399; white-space: nowrap">超长阈值:</span>
                <el-slider v-model="localThreshold" :min="6" :max="10" :step="0.5" style="width: 100px; flex-shrink: 0" />
                <el-input-number v-model="localThreshold" :min="0" :max="24" :step="0.5" :precision="1" size="small" style="width: 100px; flex-shrink: 0" />
              </div>
              <Echart :options="personalDailyChartOptions" height="300px" />
            </el-card>
          </el-col>
          <el-col :span="10">
            <el-card shadow="hover">
              <div style="margin-bottom: 8px; font-size: 14px; color: #606266">班次分布</div>
              <Echart :options="personalShiftPieOptions" height="300px" />
            </el-card>
          </el-col>
        </el-row>

        <div style="overflow-x: auto;">
          <el-table :data="localDailyStats" border stripe size="small" max-height="400">
            <ColumnWithTip prop="date" label="日期" width="90" :annotation="checkinDetailAnnMap['date']" />
            <ColumnWithTip prop="scheduled_hours" label="排班工时" width="70" :annotation="checkinDetailAnnMap['scheduled_hours']">
              <template #default="{ row }">
                {{ row.scheduled_hours ? row.scheduled_hours.toFixed(1) + 'h' : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="遵时率" width="70" :annotation="checkinDetailAnnMap['punctuality_rate']">
              <template #default="{ row }">
                {{ row.punctuality_rate != null ? row.punctuality_rate.toFixed(2) + '%' : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="通话时长" width="70" :annotation="checkinDetailAnnMap['call_duration']">
              <template #default="{ row }">
                {{ row.call_duration != null ? row.call_duration.toFixed(1) + 'h' : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="整理时长" width="70" :annotation="checkinDetailAnnMap['organize_duration']">
              <template #default="{ row }">
                {{ row.organize_duration != null ? row.organize_duration.toFixed(1) + 'h' : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="工时利用率" width="80" :annotation="checkinDetailAnnMap['utilization_rate']">
              <template #default="{ row }">
                {{ row.utilization_rate != null ? row.utilization_rate.toFixed(2) + '%' : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="班表出勤率" width="80" :annotation="checkinDetailAnnMap['attendance_rate']">
              <template #default="{ row }">
                {{ row.attendance_rate != null ? row.attendance_rate.toFixed(2) + '%' : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="培训(分)" width="65" :annotation="checkinDetailAnnMap['training_minutes']">
              <template #default="{ row }">
                {{ row.training_minutes || 0 }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="系统遵时率" width="80" :annotation="checkinDetailAnnMap['computed_punctuality_rate']">
              <template #default="{ row }">
                {{ row.computed_punctuality_rate != null ? row.computed_punctuality_rate.toFixed(2) + '%' : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip prop="checkin_time" label="签到时间" width="110" :annotation="checkinDetailAnnMap['checkin_time']">
              <template #default="{ row }">
                {{ row.checkin_time ? row.checkin_time.slice(11, 16) : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip prop="checkout_time" label="签退时间" width="110" :annotation="checkinDetailAnnMap['checkout_time']">
              <template #default="{ row }">
                {{ row.checkout_time ? row.checkout_time.slice(11, 16) : '-' }}
              </template>
            </ColumnWithTip>
            <ColumnWithTip prop="duration" label="签入工时" width="80" :annotation="checkinDetailAnnMap['duration']">
              <template #default="{ row }">
                <span :class="{ 'text-danger': row.is_long_hour }">{{ row.duration.toFixed(1) }}h</span>
              </template>
            </ColumnWithTip>
            <ColumnWithTip prop="status" label="状态" width="70" :annotation="checkinDetailAnnMap['status']">
              <template #default="{ row }">
                <el-tag v-if="row.status === '正常'" type="success" size="small">正常</el-tag>
                <el-tag v-else-if="row.status === '迟到'" type="warning" size="small">迟到</el-tag>
                <el-tag v-else-if="row.status === '早退'" type="warning" size="small">早退</el-tag>
                <el-tag v-else-if="row.status === '缺勤'" type="danger" size="small">缺勤</el-tag>
                <el-tag v-else-if="row.status === '请假'" type="info" size="small">请假</el-tag>
                <el-tag v-else-if="row.status === '休息'" type="info" size="small">休息</el-tag>
                <span v-else>-</span>
              </template>
            </ColumnWithTip>
            <ColumnWithTip prop="late_minutes" label="晚签" width="60" :annotation="checkinDetailAnnMap['late_minutes']">
              <template #default="{ row }">
                <span v-if="row.late_minutes > 0" class="text-danger">{{ row.late_minutes }}分</span>
                <span v-else>-</span>
              </template>
            </ColumnWithTip>
            <ColumnWithTip prop="early_minutes" label="提前签出" width="70" :annotation="checkinDetailAnnMap['early_minutes']">
              <template #default="{ row }">
                <span v-if="row.early_minutes > 0" class="text-danger">{{ row.early_minutes }}分</span>
                <span v-else>-</span>
              </template>
            </ColumnWithTip>
            <ColumnWithTip prop="shift_name" label="班次" width="80" :annotation="checkinDetailAnnMap['shift_name']">
              <template #default="{ row }">
                <el-tag v-if="row.shift_name === '早班'" type="primary" size="small">早班</el-tag>
                <el-tag v-else-if="row.shift_name === '中班'" type="warning" size="small">中班</el-tag>
                <el-tag v-else type="info" size="small">{{ row.shift_name }}</el-tag>
              </template>
            </ColumnWithTip>
            <ColumnWithTip label="超长" width="60" :annotation="checkinDetailAnnMap['is_long_hour']">
              <template #default="{ row }">
                <el-tag v-if="row.is_long_hour" type="danger" size="small">是</el-tag>
                <span v-else>-</span>
              </template>
            </ColumnWithTip>
          </el-table>
        </div>
      </template>
      <div v-else style="text-align: center; padding: 40px; color: #999">加载中...</div>
    </el-drawer>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, watch } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createPieOptions, createBarOptions, createLineOptions, createHorizontalBarOptions, CHART_COLORS } from '../utils/echarts'
import { getYesterday } from '../utils/date'
import { useUserStore } from '../stores/user'
const userStore = useUserStore()
import { downloadBlob } from '../utils/download'
import { usePersistedFilters } from '../composables/usePersistedFilters'
import ColumnWithTip from '../components/ColumnWithTip.vue'
import { useFieldAnnotations } from '../composables/useFieldAnnotations'

const tableData = ref([])
const teams = ref([])
const currentPage = ref(1)
const pageSize = ref(20)

const drawerVisible = ref(false)
const personalDetail = ref(null)
const drawerTitle = ref('')
const localThreshold = ref(9.5)

const checkinAnnotator = useFieldAnnotations('checkin')
const checkinDetailAnnotator = useFieldAnnotations('checkin_detail')
const checkinAnnMap = ref({})
const checkinDetailAnnMap = ref({})

watch(personalDetail, (val) => {
  if (val && val.summary && val.summary.long_hour_threshold) {
    localThreshold.value = val.summary.long_hour_threshold
  }
}, { immediate: true })

const localDailyStats = computed(() => {
  const detail = personalDetail.value
  if (!detail || !detail.daily_stats) return []
  const threshold = localThreshold.value
  return detail.daily_stats.map(d => ({
    ...d,
    is_long_hour: d.duration > threshold
  }))
})

const localLongHourDays = computed(() => {
  return localDailyStats.value.filter(d => d.is_long_hour).length
})

const paginatedData = computed(() => {
  let data = tableData.value
  if (filterType.value === 'overtime') {
    data = data.filter(d => d.hour_status === 'overtime')
  } else if (filterType.value === 'undertime') {
    data = data.filter(d => d.hour_status === 'undertime')
  } else if (filterType.value === 'name') {
    data = data.filter(d => d.name === filterValue.value)
  } else if (filterType.value === 'team') {
    data = data.filter(d => d.team === filterValue.value)
  }
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return data.slice(start, end)
})

const { filters: searchForm, isRestored: searchFormRestored, resetFilters: resetSearchForm } = usePersistedFilters(
  'checkin-report-filters',
  {
    type: 'day',
    date: getYesterday(),
    month: new Date().toISOString().slice(0, 7),
    start_date: '',
    end_date: '',
    name: '',
    emp_no: '',
    team: ''
  }
)

const stats = reactive({
  total_checkins: 0,
  emp_count: 0,
  total_hours: 0,
  avg_hours: 0,
  overtime_count: 0,
  undertime_count: 0
})

const summaryAnn = computed(() => ({
  total_scheduled_hours: checkinDetailAnnMap.value['summary_total_scheduled_hours'],
  total_hours: checkinDetailAnnMap.value['summary_total_hours'],
  team_avg_hours: checkinDetailAnnMap.value['summary_team_avg_hours'],
  attend_days: checkinDetailAnnMap.value['summary_attend_days'],
  scheduled_days: checkinDetailAnnMap.value['summary_scheduled_days'],
  long_hour_days: checkinDetailAnnMap.value['summary_long_hour_days'],
  late_days: checkinDetailAnnMap.value['summary_late_days'],
  early_days: checkinDetailAnnMap.value['summary_early_days'],
  total_call_duration: checkinDetailAnnMap.value['summary_total_call_duration'],
  total_organize_duration: checkinDetailAnnMap.value['summary_total_organize_duration'],
  total_training_minutes: checkinDetailAnnMap.value['summary_total_training_minutes'],
}))

const summaryTip = (key) => {
  const a = summaryAnn.value[key]
  if (!a || !(a.source || a.formula || a.description)) return null
  return a
}
const summaryContent = (key) => {
  const a = summaryTip(key)
  if (!a) return ''
  const parts = []
  if (a.source) parts.push('数据来源：' + a.source)
  if (a.formula) parts.push('计算公式：' + a.formula)
  if (a.description) parts.push('口径说明：' + a.description)
  return parts.join('\n')
}

const filterType = ref('')
const filterValue = ref('')

const overtimeNames = computed(() => {
  return tableData.value.filter(d => d.hour_status === 'overtime').map(d => d.name).slice(0, 5)
})

const undertimeNames = computed(() => {
  return tableData.value.filter(d => d.hour_status === 'undertime').map(d => d.name).slice(0, 5)
})

const chartType = ref('bar')

const hoursChartOptions = computed(() => {
  if (!tableData.value.length) return {}
  const data = [...tableData.value].sort((a, b) => b.total_hours - a.total_hours).slice(0, 10)
  if (chartType.value === 'line') {
    return createLineOptions(data.map(d => d.name), data.map(d => d.total_hours.toFixed(1)), '员工工时排名', '姓名', '工时(h)')
  }
  return createBarOptions(data.map(d => d.name), data.map(d => d.total_hours.toFixed(1)), '员工工时排名', '姓名', '工时(h)')
})

const checkinCountOptions = computed(() => {
  if (!tableData.value.length) return {}
  const data = [...tableData.value].sort((a, b) => a.checkin_count - b.checkin_count).slice(-10)
  return createHorizontalBarOptions(data.map(d => d.name), data.map(d => d.checkin_count), '员工签入次数排名', '姓名', '签入次数')
})

const deptHoursOptions = computed(() => {
  if (!tableData.value.length) return {}
  const teamMap = {}
  const peopleMap = {}
  tableData.value.forEach(d => {
    const team = d.team || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = 0
      peopleMap[team] = new Set()
    }
    teamMap[team] += d.total_hours
    peopleMap[team].add(d.name)
  })
  const data = Object.entries(teamMap).map(([name, value]) => ({
    name,
    value: Math.round(value),
    peopleCount: peopleMap[name].size,
    avgHours: (value / peopleMap[name].size).toFixed(1)
  }))
    .sort((a, b) => b.value - a.value).slice(0, 8)
  return createPieOptions(data, '班组工时分布')
})

const personalDailyChartOptions = computed(() => {
  const detail = personalDetail.value
  if (!detail || !detail.daily_stats || !detail.daily_stats.length) return {}
  const dates = detail.daily_stats.map(d => d.date.slice(5))
  const durations = detail.daily_stats.map(d => d.duration)
  const scheduled = detail.daily_stats.map(d => d.scheduled_hours || null)
  const threshold = localThreshold.value
  return {
    title: { text: '', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        let html = `<strong>${params[0].axisValue}</strong><br/>`
        params.forEach(p => {
          if (p.value !== null && p.value !== undefined) {
            html += `${p.marker} ${p.seriesName}: ${typeof p.value === 'number' ? p.value.toFixed(1) : p.value}h<br/>`
          }
        })
        return html
      }
    },
    legend: { data: ['实际工时', '排班工时'], bottom: 0 },
    grid: { left: '3%', right: '4%', bottom: '18%', containLabel: true },
    xAxis: { type: 'category', data: dates, name: '日期' },
    yAxis: { type: 'value', name: '工时(h)', min: 0 },
    series: [{
      name: '实际工时',
      type: 'line',
      data: durations,
      smooth: true,
      itemStyle: { color: CHART_COLORS[0] },
      areaStyle: { opacity: 0.3, color: CHART_COLORS[0] },
      markLine: {
        silent: true,
        data: [{ yAxis: threshold, label: { formatter: threshold + 'h 警戒线' }, lineStyle: { color: '#ee6666', type: 'dashed' } }]
      }
    }, {
      name: '排班工时',
      type: 'line',
      data: scheduled,
      smooth: true,
      lineStyle: { type: 'dashed', color: '#91cc75' },
      itemStyle: { color: '#91cc75' },
      symbol: 'none'
    }]
  }
})

const personalShiftPieOptions = computed(() => {
  const detail = personalDetail.value
  if (!detail || !detail.summary) return {}
  const data = [
    { name: '早班', value: detail.summary.morning_shift_days },
    { name: '中班', value: detail.summary.mid_shift_days },
    { name: '晚班', value: detail.summary.night_shift_days }
  ].filter(d => d.value > 0)
  if (!data.length) return {}
  return createPieOptions(data, '班次分布')
})

function toggleFilter(type) {
  if (filterType.value === type) {
    filterType.value = ''
    filterValue.value = ''
  } else {
    filterType.value = type
    filterValue.value = ''
  }
  currentPage.value = 1
}

function clearFilter() {
  filterType.value = ''
  filterValue.value = ''
  currentPage.value = 1
}

function handleHoursChartClick(params) {
  const name = params.name
  if (filterType.value === 'name' && filterValue.value === name) {
    clearFilter()
  } else {
    filterType.value = 'name'
    filterValue.value = name
    currentPage.value = 1
  }
}

function handleCheckinChartClick(params) {
  const name = params.name
  if (filterType.value === 'name' && filterValue.value === name) {
    clearFilter()
  } else {
    filterType.value = 'name'
    filterValue.value = name
    currentPage.value = 1
  }
}

function handleTeamChartClick(params) {
  const team = params.name
  if (filterType.value === 'team' && filterValue.value === team) {
    clearFilter()
  } else {
    filterType.value = 'team'
    filterValue.value = team
    currentPage.value = 1
  }
}

function handleTypeChange() {
  const now = new Date()
  
  if (searchForm.type === 'day') {
    searchForm.date = getYesterday()
    searchForm.month = ''
    searchForm.start_date = ''
    searchForm.end_date = ''
  } else if (searchForm.type === 'month') {
    searchForm.date = ''
    searchForm.month = now.toISOString().slice(0, 7)
    searchForm.start_date = ''
    searchForm.end_date = ''
  } else {
    searchForm.date = ''
    searchForm.month = ''
    searchForm.start_date = new Date(now.getFullYear(), now.getMonth(), 1).toISOString().slice(0, 10)
    searchForm.end_date = getYesterday()
  }
}

async function loadTeams() {
  try {
    const res = await api.get('/employees/teams')
    teams.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

async function loadData() {
  try {
    const params = {}
    
    if (searchForm.type === 'day' && searchForm.date) {
      params.date = searchForm.date
    } else if (searchForm.type === 'month' && searchForm.month) {
      params.year_month = searchForm.month
    } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
      params.start_date = searchForm.start_date
      params.end_date = searchForm.end_date
    }
    
    if (searchForm.name) params.name = searchForm.name
    if (searchForm.emp_no) params.emp_no = searchForm.emp_no
    if (searchForm.team) params.team = searchForm.team
    
    const res = await api.get('/checkins/report', { params })
    
    stats.total_checkins = res.data.stats.total_checkins
    stats.emp_count = res.data.stats.emp_count
    stats.total_hours = res.data.stats.total_hours
    stats.avg_hours = res.data.stats.avg_hours
    stats.overtime_count = res.data.stats.overtime_count || 0
    stats.undertime_count = res.data.stats.undertime_count || 0
    filterType.value = ''
    filterValue.value = ''
    tableData.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

function handleExport() {
  const params = {}
  if (searchForm.type === 'day' && searchForm.date) {
    params.date = searchForm.date
  } else if (searchForm.type === 'month' && searchForm.month) {
    params.year_month = searchForm.month
  } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
    params.start_date = searchForm.start_date
    params.end_date = searchForm.end_date
  }
  if (searchForm.name) params.name = searchForm.name
  if (searchForm.emp_no) params.emp_no = searchForm.emp_no
  if (searchForm.team) params.team = searchForm.team
  downloadBlob('/checkins/report/export', params, `checkin_report.csv`)
}

function getDetailDateRange() {
  let startDate, endDate
  if (searchForm.type === 'day' && searchForm.date) {
    endDate = searchForm.date
    startDate = endDate.slice(0, 7) + '-01'
  } else if (searchForm.type === 'month' && searchForm.month) {
    startDate = searchForm.month + '-01'
    const [y, m] = searchForm.month.split('-').map(Number)
    const lastDay = new Date(y, m, 0).getDate()
    endDate = `${searchForm.month}-${String(lastDay).padStart(2, '0')}`
  } else if (searchForm.type === 'range' && searchForm.start_date && searchForm.end_date) {
    startDate = searchForm.start_date
    endDate = searchForm.end_date
  } else {
    const now = new Date()
    endDate = getYesterday()
    startDate = now.getFullYear() + '-' + String(now.getMonth() + 1).padStart(2, '0') + '-01'
  }
  return { startDate, endDate }
}

function openDetail(row) {
  drawerTitle.value = `${row.name}（${row.emp_no}）多维统计`
  personalDetail.value = null
  drawerVisible.value = true
  loadPersonalDetail(row.emp_no)
}

async function loadPersonalDetail(empNo) {
  try {
    const { startDate, endDate } = getDetailDateRange()
    const res = await api.get('/checkins/personal-report', {
      params: { emp_no: empNo, start_date: startDate, end_date: endDate }
    })
    personalDetail.value = res.data
  } catch (e) {
    ElMessage.error('加载个人详情失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(() => {
  if (!searchFormRestored) {
    handleTypeChange()
  }
  loadTeams()
  loadData()
  checkinAnnotator.loadAnnotations().then(m => { checkinAnnMap.value = m })
  checkinDetailAnnotator.loadAnnotations().then(m => { checkinDetailAnnMap.value = m })
})
</script>

<style scoped>
.stats-row {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.text-danger {
  color: #ee6666;
  font-weight: bold;
}
.stat-custom {
  text-align: center;
}
.stat-custom .stat-label {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
}
.stat-custom .stat-value {
  display: flex;
  align-items: baseline;
  justify-content: center;
  gap: 2px;
}
.stat-custom .stat-number {
  font-size: 24px;
  color: #303133;
}
.stat-custom .stat-sub {
  font-size: 13px;
  color: #909399;
}
.tip-ico {
  color: #1a73e8;
  font-style: normal;
  cursor: help;
  font-size: 14px;
  margin-left: 2px;
}
.el-drawer__body :deep(.echart-container) {
  min-height: 0;
}
</style>