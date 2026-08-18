<template>
  <div class="checkin-report">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>签入签出报表</span>
          <el-button v-if="userStore.hasPermission('checkin_report.export')" type="success" size="small" @click="handleExport">导出</el-button>
        </div>
      </template>

      <div class="section-toolbar">
        <el-button size="small" type="primary" plain @click="showSearch = !showSearch">
          {{ showSearch ? '收起搜索' : '展开搜索' }}
        </el-button>
        <el-button v-if="activeTab === 'summary'" size="small" type="primary" plain @click="showCharts = !showCharts">
          {{ showCharts ? '收起图表' : '展开图表' }}
        </el-button>
        <el-button v-if="activeTab === 'summary'" size="small" type="warning" plain @click="columnSelectorVisible = true">自定义列</el-button>
      </div>

      <div v-show="showSearch" class="section-search-area">
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
      </div>

      <div style="margin-bottom: 12px">
        <FieldFilterPanel
          :fields="summaryFilterFields"
          v-model="summaryFilter.conditions"
          persist-key="checkin-report-summary-filter"
          @change="handleSummaryFilterChange"
        />
      </div>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="汇总" name="summary">
          <el-row :gutter="20" class="stats-row">
        <el-col :span="3">
          <el-statistic title="签入人次" :value="stats.total_checkins" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="总人数" :value="stats.emp_count" />
        </el-col>
        <el-col :span="3">
          <el-statistic title="总时长" :value="stats.total_hours" :precision="1">
            <template #suffix>小时</template>
          </el-statistic>
        </el-col>
        <el-col :span="3">
          <el-statistic title="平均时长" :value="stats.avg_hours" :precision="1">
            <template #suffix>小时</template>
          </el-statistic>
        </el-col>
        <el-col :span="3">
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
        <el-col :span="3">
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
        <el-col :span="3">
          <el-statistic title="晚签人数" :value="lateEarlyStats.latePeople">
            <template #suffix>
              <el-tooltip v-if="lateEarlyStats.latePeople > 0" content="期间内至少晚签1次即算1人" placement="top">
                <el-button type="warning" link @click="toggleFilter('late')">
                  {{ filterType === 'late' ? '已筛选' : '点击筛选' }}
                </el-button>
              </el-tooltip>
            </template>
          </el-statistic>
        </el-col>
        <el-col :span="3">
          <el-statistic title="早退人数" :value="lateEarlyStats.earlyPeople">
            <template #suffix>
              <el-tooltip v-if="lateEarlyStats.earlyPeople > 0" content="期间内至少早退1次即算1人" placement="top">
                <el-button type="warning" link @click="toggleFilter('early')">
                  {{ filterType === 'early' ? '已筛选' : '点击筛选' }}
                </el-button>
              </el-tooltip>
            </template>
          </el-statistic>
        </el-col>
      </el-row>

      <div v-if="showCharts" class="summary-charts">
      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 12px">
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 6px; font-size: 14px; color: #606266">签入次数区间分布（点击区间筛选）</div>
            <Echart :options="checkinBucketOptions" height="180px" @click="handleCheckinRangeClick" />
          </el-card>
        </el-col>
        <el-col :span="12">
          <el-card shadow="hover">
            <div style="margin-bottom: 6px; font-size: 14px; color: #606266">班组晚签/早退人数（点击筛选）</div>
            <Echart :options="lateEarlyByTeamOptions" height="180px" @click="handleLateEarlyClick" />
          </el-card>
        </el-col>
      </el-row>

      <el-row :gutter="20" v-if="tableData.length" style="margin-bottom: 12px">
        <el-col :span="8">
          <el-card shadow="hover">
            <div style="margin-bottom: 6px; font-size: 14px; color: #606266">班组工时分布（点击班组筛选）</div>
            <Echart :options="deptHoursOptions" height="280px" @click="handleTeamChartClick" />
          </el-card>
        </el-col>
        <el-col :span="16">
          <el-card shadow="hover">
            <div style="margin-bottom: 6px; font-size: 14px; color: #606266">班组工时明细</div>
            <div style="overflow-x: auto;">
              <el-table :data="teamMetricsRanking" size="small" border stripe max-height="280" @row-click="handleTeamTableRowClick">
                <el-table-column label="排名" width="55" type="index" />
                <el-table-column label="班组" prop="team" min-width="100" />
                <el-table-column label="组长" prop="leader" min-width="70" />
                <el-table-column label="人数" width="55" prop="count" sortable />
                <el-table-column label="总工作时长" width="95" sortable prop="total_hours">
                  <template #default="{ row }">{{ row.total_hours.toFixed(1) }}</template>
                </el-table-column>
                <el-table-column label="总排班工时" width="95" sortable prop="scheduled_hours">
                  <template #default="{ row }">{{ row.scheduled_hours.toFixed(1) }}</template>
                </el-table-column>
                <el-table-column label="人均工作时长" width="95" sortable prop="avg_hours">
                  <template #default="{ row }">{{ row.avg_hours.toFixed(1) }}</template>
                </el-table-column>
                <el-table-column label="系统遵时率" width="90" sortable prop="computed_punctuality_rate">
                  <template #default="{ row }">{{ row.computed_punctuality_rate != null ? row.computed_punctuality_rate.toFixed(2) + '%' : '-' }}</template>
                </el-table-column>
                <el-table-column label="遵时率" width="85" sortable prop="avg_punctuality_rate">
                  <template #default="{ row }">{{ row.avg_punctuality_rate != null ? row.avg_punctuality_rate.toFixed(2) + '%' : '-' }}</template>
                </el-table-column>
                <el-table-column label="工时利用率" width="90" sortable prop="avg_utilization_rate">
                  <template #default="{ row }">{{ row.avg_utilization_rate != null ? row.avg_utilization_rate.toFixed(2) + '%' : '-' }}</template>
                </el-table-column>
                <el-table-column label="班表出勤率" width="90" sortable prop="avg_attendance_rate">
                  <template #default="{ row }">{{ row.avg_attendance_rate != null ? row.avg_attendance_rate.toFixed(2) + '%' : '-' }}</template>
                </el-table-column>
                <el-table-column label="占比" width="75" sortable prop="total_hours">
                  <template #default="{ row }">{{ (row.total_hours / teamTotalHours * 100).toFixed(1) + '%' }}</template>
                </el-table-column>
              </el-table>
            </div>
          </el-card>
        </el-col>
        </el-row>
      </div>

      <el-table :data="paginatedData" border stripe show-summary :summary-method="summaryMethod" max-height="calc(100vh - 350px)" @sort-change="handleSortChange">
        <ColumnWithTip v-if="columnVisible('emp_no')" prop="emp_no" label="账号" width="100" :annotation="checkinAnnMap['emp_no']" />
        <ColumnWithTip v-if="columnVisible('name')" prop="name" label="用户名" width="100" :annotation="checkinAnnMap['name']" />
        <ColumnWithTip v-if="columnVisible('dept')" prop="dept" label="所属部门" min-width="150" :annotation="checkinAnnMap['dept']" />
        <ColumnWithTip v-if="columnVisible('team')" prop="team" label="班组" width="100" :annotation="checkinAnnMap['team']" />
        <ColumnWithTip v-if="columnVisible('checkin_count')" prop="checkin_count" label="签入次数" width="80" sortable="custom" :annotation="checkinAnnMap['checkin_count']" />
        <ColumnWithTip v-if="columnVisible('total_hours')" prop="total_hours" label="工作时长" width="80" sortable="custom" :annotation="checkinAnnMap['total_hours']">
          <template #default="{ row }">
            {{ row.total_hours.toFixed(1) }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('scheduled_hours')" prop="scheduled_hours" label="排班工时" width="80" sortable="custom" :annotation="checkinAnnMap['scheduled_hours']">
          <template #default="{ row }">
            {{ row.scheduled_hours != null ? row.scheduled_hours.toFixed(1) : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('hour_status_text')" prop="hour_status_text" label="工时状态" width="120" :annotation="checkinAnnMap['hour_status_text']">
          <template #default="{ row }">
            <el-tag v-if="row.hour_status === 'overtime'" type="danger" size="small">超时</el-tag>
            <el-tag v-else-if="row.hour_status === 'undertime'" type="warning" size="small">过短</el-tag>
            <el-tag v-else-if="row.hour_status === 'normal'" type="success" size="small">正常</el-tag>
            <span v-else>-</span>
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('avg_punctuality_rate')" prop="avg_punctuality_rate" label="遵时率" width="80" sortable="custom" :annotation="checkinAnnMap['avg_punctuality_rate']">
          <template #default="{ row }">
            {{ row.avg_punctuality_rate != null ? row.avg_punctuality_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('total_call_duration')" prop="total_call_duration" label="通话时长" width="80" sortable="custom" :annotation="checkinAnnMap['total_call_duration']">
          <template #default="{ row }">
            {{ row.total_call_duration != null ? row.total_call_duration.toFixed(1) + 'h' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('total_organize_duration')" prop="total_organize_duration" label="整理时长" width="80" sortable="custom" :annotation="checkinAnnMap['total_organize_duration']">
          <template #default="{ row }">
            {{ row.total_organize_duration != null ? row.total_organize_duration.toFixed(1) + 'h' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('avg_utilization_rate')" prop="avg_utilization_rate" label="工时利用率" width="90" sortable="custom" :annotation="checkinAnnMap['avg_utilization_rate']">
          <template #default="{ row }">
            {{ row.avg_utilization_rate != null ? row.avg_utilization_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('avg_attendance_rate')" prop="avg_attendance_rate" label="班表出勤率" width="90" sortable="custom" :annotation="checkinAnnMap['avg_attendance_rate']">
          <template #default="{ row }">
            {{ row.avg_attendance_rate != null ? row.avg_attendance_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('training_minutes')" prop="training_minutes" label="培训扣除(分)" width="90" sortable="custom" :annotation="checkinAnnMap['training_minutes']">
          <template #default="{ row }">
            {{ row.training_minutes != null ? row.training_minutes : 0 }}
          </template>
        </ColumnWithTip>
        <ColumnWithTip v-if="columnVisible('computed_punctuality_rate')" prop="computed_punctuality_rate" label="系统遵时率" width="90" sortable="custom" :annotation="checkinAnnMap['computed_punctuality_rate']">
          <template #default="{ row }">
            {{ row.computed_punctuality_rate != null ? row.computed_punctuality_rate.toFixed(2) + '%' : '-' }}
          </template>
        </ColumnWithTip>
        <el-table-column v-if="columnVisible('attend_days')" prop="attend_days" label="出勤天数" width="90" sortable="custom">
          <template #default="{ row }">{{ row.attend_days || 0 }}</template>
        </el-table-column>
        <el-table-column v-if="columnVisible('late_days')" prop="late_days" label="晚签天数" width="90" sortable="custom">
          <template #default="{ row }">
            <span :class="{ 'text-danger': (row.late_days || 0) > 0 }">{{ row.late_days || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="columnVisible('late_minutes')" prop="late_minutes" label="晚签总分钟" width="100" sortable="custom">
          <template #default="{ row }">
            <span :class="{ 'text-danger': (row.late_minutes || 0) > 0 }">{{ row.late_minutes || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="columnVisible('early_days')" prop="early_days" label="提前签出天数" width="110" sortable="custom">
          <template #default="{ row }">
            <span :class="{ 'text-danger': (row.early_days || 0) > 0 }">{{ row.early_days || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="columnVisible('early_minutes')" prop="early_minutes" label="提前签出总分钟" width="120" sortable="custom">
          <template #default="{ row }">
            <span :class="{ 'text-danger': (row.early_minutes || 0) > 0 }">{{ row.early_minutes || 0 }}</span>
          </template>
        </el-table-column>
        <el-table-column v-if="columnVisible('checkin_details')" label="签入明细" min-width="280">
          <template #default="{ row }">
            <template v-if="row.checkins && row.checkins.length">
              <div class="checkin-list">
                <template v-if="!expandedCheckins.has(row.emp_no)">
                  <el-tag v-for="(c, idx) in row.checkins.slice(0, 2)" :key="idx" size="small" style="margin: 2px 4px 2px 0;">
                    {{ idx + 1 }}: {{ c.checkin_time || '-' }} → {{ c.checkout_time || '-' }}
                    <span style="margin-left: 2px; font-size: 12px; color: #666;">({{ c.duration.toFixed(1) }}h)</span>
                  </el-tag>
                </template>
                <template v-else>
                  <el-tag v-for="(c, idx) in row.checkins" :key="idx" size="small" style="margin: 2px 4px 2px 0;">
                    {{ idx + 1 }}: {{ c.checkin_time || '-' }} → {{ c.checkout_time || '-' }}
                    <span style="margin-left: 2px; font-size: 12px; color: #666;">({{ c.duration.toFixed(1) }}h)</span>
                  </el-tag>
                </template>
                <div style="margin-top: 2px;">
                  <el-button link type="primary" size="small" @click="toggleCheckins(row.emp_no)">
                    <template v-if="expandedCheckins.has(row.emp_no)">收起</template>
                    <template v-else>展开全部({{ row.checkins.length }})</template>
                  </el-button>
                </div>
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
        :total="filteredData.length"
        layout="total, sizes, prev, pager, next, jumper"
        style="margin-top: 15px; justify-content: flex-end"
      />
        </el-tab-pane>

        <el-tab-pane label="时段分析" name="time">
          <div style="margin-bottom: 12px; font-size: 13px; color: #909399">
            高峰期/低谷期、班次结构与分时工时利用率分析（时段口径已按班次归属处理，晚班跨午夜照常计入）
          </div>
          <el-row :gutter="16" style="margin-bottom: 16px">
            <el-col :span="16">
              <el-card shadow="hover">
                <div style="margin-bottom: 8px; font-size: 14px; color: #606266">分时签入/签出分布（高峰期识别）</div>
                <Echart :options="timeHourlyOptions" height="300px" @click="handleTimeHourlyClick" />
              </el-card>
            </el-col>
            <el-col :span="8">
              <el-card shadow="hover">
                <div style="margin-bottom: 8px; font-size: 14px; color: #606266">班次占比（点击查看班次人员）</div>
                <Echart :options="timeShiftOverallOptions" height="300px" @click="handleTimeShiftOverallClick" />
              </el-card>
            </el-col>
          </el-row>
          <el-row :gutter="16">
            <el-col :span="12">
              <el-card shadow="hover">
                <div style="margin-bottom: 8px; font-size: 14px; color: #606266">各班组班次结构（人次）</div>
                <Echart :options="timeShiftTeamOptions" height="300px" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <div style="margin-bottom: 8px; font-size: 14px; color: #606266">分时工时利用率（应排班 vs 实际在岗）</div>
                <Echart :options="timeUtilizationOptions" height="300px" />
              </el-card>
            </el-col>
          </el-row>
          <div v-if="!tableData.length" style="text-align: center; padding: 30px; color: #999">暂无数据，请选择日期后查询</div>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="columnSelectorVisible" title="自定义显示列" width="620px">
      <el-checkbox-group v-model="selectedColumns">
        <el-checkbox v-for="col in ALL_COLUMNS" :key="col.key" :label="col.key" style="margin: 4px 12px; width: 200px">
          {{ col.label }}
        </el-checkbox>
      </el-checkbox-group>
      <template #footer>
        <el-button @click="columnSelectorVisible = false">关闭</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="timeDetailVisible" :title="timeDetailTitle" width="720px">
      <template v-if="timeDetailMode === 'hour'">
        <div style="margin-bottom: 8px; font-weight: 600">签入人员（{{ timeHourPersons.checkin.length }}）</div>
        <el-table :data="timeHourPersons.checkin" size="small" max-height="260" border>
          <el-table-column prop="emp_no" label="工号" width="110" />
          <el-table-column prop="name" label="姓名" width="120" />
          <el-table-column prop="team" label="班组" />
          <el-table-column prop="time" label="签入时间" width="100" />
        </el-table>
        <div style="margin: 12px 0 8px; font-weight: 600">签出人员（{{ timeHourPersons.checkout.length }}）</div>
        <el-table :data="timeHourPersons.checkout" size="small" max-height="260" border>
          <el-table-column prop="emp_no" label="工号" width="110" />
          <el-table-column prop="name" label="姓名" width="120" />
          <el-table-column prop="team" label="班组" />
          <el-table-column prop="time" label="签出时间" width="100" />
        </el-table>
      </template>
      <template v-else>
        <div style="margin-bottom: 8px; font-weight: 600">该班次人员（共 {{ timeShiftPersons.length }} 人）</div>
        <el-table :data="timeShiftPersons" size="small" max-height="420" border>
          <el-table-column prop="emp_no" label="工号" width="110" />
          <el-table-column prop="name" label="姓名" width="120" />
          <el-table-column prop="team" label="班组" />
          <el-table-column prop="days" label="排班天数" width="100" sortable />
        </el-table>
      </template>
      <template #footer>
        <el-button @click="timeDetailVisible = false">关闭</el-button>
      </template>
    </el-dialog>

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
            <el-statistic :precision="1" :value="personalDetail.summary.total_scheduled_hours">
              <template #title>
                <span>排班总工时 <el-tooltip v-if="summaryTip('total_scheduled_hours')" :content="summaryContent('total_scheduled_hours')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1" :value="personalDetail.summary.total_hours">
              <template #title>
                <span>累计工时 <el-tooltip v-if="summaryTip('total_hours')" :content="summaryContent('total_hours')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1" :value="personalDetail.summary.team_avg_hours">
              <template #title>
                <span>班组平均工时 <el-tooltip v-if="summaryTip('team_avg_hours')" :content="summaryContent('team_avg_hours')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
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
            <el-statistic :value="localLongHourDays">
              <template #title>
                <span>超长工时 <el-tooltip v-if="summaryTip('long_hour_days')" :content="summaryContent('long_hour_days')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
              <template #suffix>天</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :value="personalDetail.summary.late_days">
              <template #title>
                <span>晚签天数 <el-tooltip v-if="summaryTip('late_days')" :content="summaryContent('late_days')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
              <template #suffix>天</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :value="personalDetail.summary.early_days">
              <template #title>
                <span>提前签出天数 <el-tooltip v-if="summaryTip('early_days')" :content="summaryContent('early_days')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
              <template #suffix>天</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1" :value="personalDetail.summary.total_call_duration || 0">
              <template #title>
                <span>通话总时长 <el-tooltip v-if="summaryTip('total_call_duration')" :content="summaryContent('total_call_duration')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :precision="1" :value="personalDetail.summary.total_organize_duration || 0">
              <template #title>
                <span>整理总时长 <el-tooltip v-if="summaryTip('total_organize_duration')" :content="summaryContent('total_organize_duration')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
              <template #suffix>h</template>
            </el-statistic>
          </el-col>
          <el-col :span="3">
            <el-statistic :value="personalDetail.summary.total_training_minutes || 0">
              <template #title>
                <span>培训总时长 <el-tooltip v-if="summaryTip('total_training_minutes')" :content="summaryContent('total_training_minutes')" effect="light" placement="top"><i class="tip-ico">ⓘ</i></el-tooltip></span>
              </template>
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
import { createPieOptions, createBarOptions, createMultiBarOptions, CHART_COLORS } from '../utils/echarts'
import { getYesterday } from '../utils/date'
import { useUserStore } from '../stores/user'
const userStore = useUserStore()
import { downloadBlob } from '../utils/download'
import { usePersistedFilters } from '../composables/usePersistedFilters'
import ColumnWithTip from '../components/ColumnWithTip.vue'
import { useFieldAnnotations } from '../composables/useFieldAnnotations'
import FieldFilterPanel from '../components/FieldFilterPanel.vue'
import { useFieldFilter } from '../composables/useFieldFilter'

const tableData = ref([])
const teams = ref([])
const teamLeaders = ref({})
const currentPage = ref(1)
const pageSize = ref(20)
const sortBy = ref('')
const sortOrder = ref('')

const ALL_COLUMNS = [
  { key: 'emp_no', label: '账号' },
  { key: 'name', label: '用户名' },
  { key: 'dept', label: '所属部门' },
  { key: 'team', label: '班组' },
  { key: 'checkin_count', label: '签入次数' },
  { key: 'total_hours', label: '工作时长' },
  { key: 'scheduled_hours', label: '排班工时' },
  { key: 'hour_status_text', label: '工时状态' },
  { key: 'avg_punctuality_rate', label: '遵时率' },
  { key: 'total_call_duration', label: '通话时长' },
  { key: 'total_organize_duration', label: '整理时长' },
  { key: 'avg_utilization_rate', label: '工时利用率' },
  { key: 'avg_attendance_rate', label: '班表出勤率' },
  { key: 'training_minutes', label: '培训扣除(分)' },
  { key: 'computed_punctuality_rate', label: '系统遵时率' },
  { key: 'attend_days', label: '出勤天数' },
  { key: 'late_days', label: '晚签天数' },
  { key: 'late_minutes', label: '晚签总分钟' },
  { key: 'early_days', label: '提前签出天数' },
  { key: 'early_minutes', label: '提前签出总分钟' },
  { key: 'checkin_details', label: '签入明细' }
]
const COLUMNS_KEY = 'checkin-report-columns'
const DEFAULT_COLUMNS = ALL_COLUMNS.map(c => c.key)

function loadSelectedColumns() {
  try {
    const saved = localStorage.getItem(COLUMNS_KEY)
    return saved ? JSON.parse(saved) : [...DEFAULT_COLUMNS]
  } catch { return [...DEFAULT_COLUMNS] }
}

const columnSelectorVisible = ref(false)
const selectedColumns = ref(loadSelectedColumns())

watch(selectedColumns, (val) => {
  localStorage.setItem(COLUMNS_KEY, JSON.stringify(val))
}, { deep: true })

function columnVisible(key) {
  return selectedColumns.value.includes(key)
}

const SUMMABLE_COLUMNS = new Set([
  'checkin_count', 'total_hours', 'scheduled_hours', 'total_call_duration', 'total_organize_duration',
  'training_minutes', 'attend_days', 'late_days', 'late_minutes', 'early_days', 'early_minutes'
])
const DECIMAL_COLUMNS = new Set([
  'total_hours', 'scheduled_hours', 'total_call_duration', 'total_organize_duration'
])

function summaryMethod({ columns, data }) {
  const source = filteredData.value && filteredData.value.length ? filteredData.value : data
  return columns.map(col => {
    const key = col.property
    if (!key || !SUMMABLE_COLUMNS.has(key)) return ''
    const total = source.reduce((sum, row) => {
      const val = row[key]
      return sum + (typeof val === 'number' && isFinite(val) ? val : 0)
    }, 0)
    if (DECIMAL_COLUMNS.has(key)) return total.toFixed(1)
    return String(Math.round(total))
  })
}

const savedTab = sessionStorage.getItem('checkin-report-active-tab')
const activeTab = ref(savedTab || 'summary')
watch(activeTab, (val) => {
  sessionStorage.setItem('checkin-report-active-tab', val)
})

const showCharts = ref(JSON.parse(sessionStorage.getItem('checkin-report-show-charts') ?? 'true'))
const showSearch = ref(JSON.parse(sessionStorage.getItem('checkin-report-show-search') ?? 'false'))
watch(showCharts, (val) => {
  sessionStorage.setItem('checkin-report-show-charts', JSON.stringify(val))
})
watch(showSearch, (val) => {
  sessionStorage.setItem('checkin-report-show-search', JSON.stringify(val))
})

const teamReportData = ref([])
const expandedCheckins = ref(new Set())

function toggleCheckins(empNo) {
  const next = new Set(expandedCheckins.value)
  if (next.has(empNo)) {
    next.delete(empNo)
  } else {
    next.add(empNo)
  }
  expandedCheckins.value = next
}

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

const filteredData = computed(() => {
  let data = mergedData.value
  if (filterType.value === 'overtime') {
    data = data.filter(d => d.hour_status === 'overtime')
  } else if (filterType.value === 'undertime') {
    data = data.filter(d => d.hour_status === 'undertime')
  } else if (filterType.value === 'name') {
    data = data.filter(d => d.name === filterValue.value)
  } else if (filterType.value === 'team') {
    data = data.filter(d => d.team === filterValue.value)
  } else if (filterType.value === 'late') {
    data = data.filter(d => (d.late_days || 0) > 0)
  } else if (filterType.value === 'early') {
    data = data.filter(d => (d.early_days || 0) > 0)
  } else if (filterType.value === 'checkin_range') {
    data = data.filter(d => d.checkin_count >= filterValue.value.min && d.checkin_count <= filterValue.value.max)
  } else if (filterType.value === 'late_team') {
    data = data.filter(d => d.team === filterValue.value && (d.late_days || 0) > 0)
  } else if (filterType.value === 'early_team') {
    data = data.filter(d => d.team === filterValue.value && (d.early_days || 0) > 0)
  }
  data = summaryFilter.filtered(data)
  if (sortBy.value && sortOrder.value) {
    data = [...data].sort((a, b) => {
      const aVal = a[sortBy.value] ?? -1
      const bVal = b[sortBy.value] ?? -1
      return sortOrder.value === 'ascending' ? aVal - bVal : bVal - aVal
    })
  }
  return data
})

const paginatedData = computed(() => {
  const data = filteredData.value
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return data.slice(start, end)
})

function handleSortChange({ prop, order }) {
  sortBy.value = prop || ''
  sortOrder.value = order || ''
  currentPage.value = 1
}

const teamReportMap = computed(() => {
  const m = {}
  teamReportData.value.forEach(d => { m[d.emp_no] = d })
  return m
})

const mergedData = computed(() => {
  return tableData.value.map(row => {
    const tr = teamReportMap.value[row.emp_no] || {}
    return {
      ...row,
      attend_days: tr.attend_days || 0,
      late_days: tr.late_days || 0,
      late_minutes: tr.late_minutes || 0,
      early_days: tr.early_days || 0,
      early_minutes: tr.early_minutes || 0
    }
  })
})

const lateEarlyStats = computed(() => {
  const data = mergedData.value
  return {
    latePeople: data.filter(d => (d.late_days || 0) > 0).length,
    earlyPeople: data.filter(d => (d.early_days || 0) > 0).length
  }
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

const summaryFilterFields = [
  { key: 'total_hours', label: '工作时长', unit: 'number', get: row => row.total_hours ?? null },
  { key: 'scheduled_hours', label: '排班工时', unit: 'number', get: row => row.scheduled_hours ?? null },
  { key: 'checkin_count', label: '签入次数', unit: 'number', get: row => row.checkin_count ?? null },
  { key: 'avg_punctuality_rate', label: '遵时率(%)', unit: 'percent', get: row => row.avg_punctuality_rate ?? null },
  { key: 'computed_punctuality_rate', label: '系统遵时率(%)', unit: 'percent', get: row => row.computed_punctuality_rate ?? null },
  { key: 'avg_utilization_rate', label: '工时利用率(%)', unit: 'percent', get: row => row.avg_utilization_rate ?? null },
  { key: 'avg_attendance_rate', label: '班表出勤率(%)', unit: 'percent', get: row => row.avg_attendance_rate ?? null },
  { key: 'total_call_duration', label: '通话时长', unit: 'number', get: row => row.total_call_duration ?? null },
  { key: 'total_organize_duration', label: '整理时长', unit: 'number', get: row => row.total_organize_duration ?? null },
  { key: 'training_minutes', label: '培训扣除(分)', unit: 'number', get: row => row.training_minutes ?? null },
  { key: 'late_days', label: '晚签天数', unit: 'number', get: row => row.late_days ?? null },
  { key: 'late_minutes', label: '晚签总分钟', unit: 'number', get: row => row.late_minutes ?? null },
  { key: 'early_days', label: '提前签出天数', unit: 'number', get: row => row.early_days ?? null },
  { key: 'early_minutes', label: '提前签出总分钟', unit: 'number', get: row => row.early_minutes ?? null }
]
const summaryFilter = useFieldFilter(summaryFilterFields, { persistKey: 'checkin-report-summary-filter' })
function handleSummaryFilterChange() {
  currentPage.value = 1
}

const overtimeNames = computed(() => {
  return tableData.value.filter(d => d.hour_status === 'overtime').map(d => d.name).slice(0, 5)
})

const undertimeNames = computed(() => {
  return tableData.value.filter(d => d.hour_status === 'undertime').map(d => d.name).slice(0, 5)
})

const teamMetricsRanking = computed(() => {
  const data = mergedData.value
  if (!data.length) return []
  const teamMap = {}
  data.forEach(d => {
    const team = d.team || '未知班组'
    if (!teamMap[team]) {
      teamMap[team] = {
        count: 0,
        total_hours: 0,
        scheduled_hours: 0,
        avg_punctuality_rate_sum: 0,
        avg_punctuality_rate_n: 0,
        computed_punctuality_rate_sum: 0,
        computed_punctuality_rate_n: 0,
        avg_utilization_rate_sum: 0,
        avg_utilization_rate_n: 0,
        avg_attendance_rate_sum: 0,
        avg_attendance_rate_n: 0,
        total_call_duration: 0,
        total_organize_duration: 0,
        training_minutes: 0,
        late_people: 0,
        late_days: 0,
        early_people: 0,
        early_days: 0
      }
    }
    const t = teamMap[team]
    t.count++
    t.total_hours += d.total_hours || 0
    t.scheduled_hours += d.scheduled_hours != null ? d.scheduled_hours : 0
    if (d.avg_punctuality_rate != null) {
      t.avg_punctuality_rate_sum += d.avg_punctuality_rate
      t.avg_punctuality_rate_n++
    }
    if (d.computed_punctuality_rate != null) {
      t.computed_punctuality_rate_sum += d.computed_punctuality_rate
      t.computed_punctuality_rate_n++
    }
    if (d.avg_utilization_rate != null) {
      t.avg_utilization_rate_sum += d.avg_utilization_rate
      t.avg_utilization_rate_n++
    }
    if (d.avg_attendance_rate != null) {
      t.avg_attendance_rate_sum += d.avg_attendance_rate
      t.avg_attendance_rate_n++
    }
    t.total_call_duration += d.total_call_duration || 0
    t.total_organize_duration += d.total_organize_duration || 0
    t.training_minutes += d.training_minutes || 0
    if ((d.late_days || 0) > 0) {
      t.late_people++
      t.late_days += d.late_days
    }
    if ((d.early_days || 0) > 0) {
      t.early_people++
      t.early_days += d.early_days
    }
  })
  return Object.entries(teamMap)
    .map(([team, t]) => ({
      team,
      leader: teamLeaders.value[team] || '',
      count: t.count,
      total_hours: t.total_hours,
      scheduled_hours: t.scheduled_hours,
      avg_hours: t.count > 0 ? t.total_hours / t.count : 0,
      avg_punctuality_rate: t.avg_punctuality_rate_n > 0 ? t.avg_punctuality_rate_sum / t.avg_punctuality_rate_n : null,
      computed_punctuality_rate: t.computed_punctuality_rate_n > 0 ? t.computed_punctuality_rate_sum / t.computed_punctuality_rate_n : null,
      avg_utilization_rate: t.avg_utilization_rate_n > 0 ? t.avg_utilization_rate_sum / t.avg_utilization_rate_n : null,
      avg_attendance_rate: t.avg_attendance_rate_n > 0 ? t.avg_attendance_rate_sum / t.avg_attendance_rate_n : null,
      total_call_duration: t.total_call_duration,
      total_organize_duration: t.total_organize_duration,
      training_minutes: t.training_minutes,
      late_people: t.late_people,
      late_days: t.late_days,
      early_people: t.early_people,
      early_days: t.early_days
    }))
    .sort((a, b) => b.total_hours - a.total_hours)
    .slice(0, 8)
})

const teamTotalHours = computed(() => {
  return teamMetricsRanking.value.reduce((s, t) => s + t.total_hours, 0)
})

const deptHoursOptions = computed(() => {
  const ranking = teamMetricsRanking.value
  if (!ranking.length) return {}
  const data = ranking.map(t => ({
    name: t.team,
    value: Math.round(t.total_hours),
    peopleCount: t.count,
    avgHours: t.avg_hours.toFixed(1)
  }))
  return createPieOptions(data, '班组工时分布')
})

const checkinBuckets = computed(() => {
  const data = mergedData.value
  if (!data.length) return []
  const max = Math.max(...data.map(d => d.checkin_count))
  const width = Math.max(1, Math.ceil(max / 8))
  const buckets = []
  for (let i = 0; i < 8; i++) {
    const start = i * width
    const end = i === 7 ? max : start + width - 1
    const count = data.filter(d => d.checkin_count >= start && d.checkin_count <= end).length
    buckets.push({ name: `${start}~${end}次`, min: start, max: end, value: count })
  }
  return buckets
})

const checkinBucketOptions = computed(() => {
  const buckets = checkinBuckets.value
  if (!buckets.length) return {}
  const data = mergedData.value
  return createBarOptions(
    buckets.map(b => b.name),
    buckets.map(b => b.value),
    '签入次数区间分布',
    '区间',
    '人数',
    (params) => {
      const bucket = buckets[params[0].dataIndex]
      const people = data
        .filter(d => d.checkin_count >= bucket.min && d.checkin_count <= bucket.max)
        .sort((a, b) => b.total_hours - a.total_hours)
        .slice(0, 5)
      let html = `<strong>${bucket.name}</strong>: ${bucket.value} 人<br/>`
      if (people.length) {
        html += people.map(p => `${p.name}: ${p.checkin_count}次 / ${p.total_hours.toFixed(1)}h`).join('<br/>')
        const totalInBucket = data.filter(d => d.checkin_count >= bucket.min && d.checkin_count <= bucket.max).length
        if (totalInBucket > people.length) {
          html += `<br/><span style="color:#909399">... 等 ${totalInBucket} 人</span>`
        }
      }
      return html
    }
  )
})

const lateEarlyByTeamOptions = computed(() => {
  const data = mergedData.value
  if (!data.length) return {}
  const teamMap = {}
  const latePeopleMap = {}
  const earlyPeopleMap = {}
  data.forEach(d => {
    const t = d.team || '未知班组'
    if (!teamMap[t]) teamMap[t] = { late: 0, early: 0 }
    if ((d.late_days || 0) > 0) {
      teamMap[t].late += 1
      if (!latePeopleMap[t]) latePeopleMap[t] = []
      latePeopleMap[t].push({ name: d.name, minutes: d.late_minutes || 0 })
    }
    if ((d.early_days || 0) > 0) {
      teamMap[t].early += 1
      if (!earlyPeopleMap[t]) earlyPeopleMap[t] = []
      earlyPeopleMap[t].push({ name: d.name, minutes: d.early_minutes || 0 })
    }
  })
  Object.keys(latePeopleMap).forEach(k => latePeopleMap[k].sort((a, b) => b.minutes - a.minutes))
  Object.keys(earlyPeopleMap).forEach(k => earlyPeopleMap[k].sort((a, b) => b.minutes - a.minutes))
  const teams = Object.keys(teamMap)
  return createMultiBarOptions(
    teams,
    [
      { name: '晚签人数', data: teams.map(t => teamMap[t].late) },
      { name: '早退人数', data: teams.map(t => teamMap[t].early) }
    ],
    '班组晚签/早退人数',
    (params) => {
      const team = params[0].name
      const lateList = latePeopleMap[team] || []
      const earlyList = earlyPeopleMap[team] || []
      const lateLabel = '晚签'
      const earlyLabel = '早退'
      let html = `<strong>${team} - ${lateLabel}: ${lateList.length}人 / ${earlyLabel}: ${earlyList.length}人</strong><br/>`
      if (!lateList.length && !earlyList.length) {
        html += `<span style="color:#909399">无晚签/早退记录</span>`
        return html
      }
      if (lateList.length) {
        html += `<span style="color:#c45656;font-weight:bold">${lateLabel}明细:</span><br/>`
        lateList.slice(0, 8).forEach(p => {
          html += `${p.name} ${lateLabel} ${p.minutes}分<br/>`
        })
        if (lateList.length > 8) {
          html += `<span style="color:#909399">... 等 ${lateList.length} 人</span><br/>`
        }
      }
      if (earlyList.length) {
        html += `<span style="color:#c45656;font-weight:bold">${earlyLabel}明细:</span><br/>`
        earlyList.slice(0, 8).forEach(p => {
          html += `${p.name} ${earlyLabel} ${p.minutes}分<br/>`
        })
        if (earlyList.length > 8) {
          html += `<span style="color:#909399">... 等 ${earlyList.length} 人</span><br/>`
        }
      }
      return html
    }
  )
})

const timeHourly = ref([])
const timeShifts = ref({ overall: [], by_team: [] })
const timeUtilization = ref([])
const timeDetailVisible = ref(false)
const timeDetailTitle = ref('')
const timeDetailMode = ref('hour')
const timeHourPersons = ref({ checkin: [], checkout: [] })
const timeShiftPersons = ref([])

const timeHourlyOptions = computed(() => {
  if (!timeHourly.value.length) return {}
  const hours = timeHourly.value.map(d => `${d.hour}点`)
  return createMultiBarOptions(hours, [
    { name: '签入人次', data: timeHourly.value.map(d => d.checkin_count) },
    { name: '签出人次', data: timeHourly.value.map(d => d.checkout_count) }
  ], '分时签入/签出分布', (params) => {
    const d = timeHourly.value[params[0].dataIndex]
    if (!d) return ''
    let html = `<strong>${d.hour}点</strong><br/>`
    const ci = d.checkin_teams || []
    const co = d.checkout_teams || []
    html += `签入 ${d.checkin_count} 人次<br/>`
    if (ci.length) {
      ci.forEach(t => { html += `　${t.team}: ${t.count} 人<br/>` })
    }
    html += `签出 ${d.checkout_count} 人次<br/>`
    if (co.length) {
      co.forEach(t => { html += `　${t.team}: ${t.count} 人<br/>` })
    }
    return html
  })
})

const timeShiftOverallOptions = computed(() => {
  const overall = timeShifts.value.overall || []
  const byTeam = timeShifts.value.by_team || []
  if (!overall.length) return {}
  const shiftTeamMap = {}
  byTeam.forEach(s => {
    if (!shiftTeamMap[s.shift_name]) shiftTeamMap[s.shift_name] = []
    shiftTeamMap[s.shift_name].push({ team: s.team, count: s.count })
  })
  return createPieOptions(overall.map(s => ({ name: s.shift_name, value: s.count })), '班次占比', CHART_COLORS, '人次', (params) => {
    let html = `<strong>${params.name}</strong><br/>人次: ${params.value} (${params.percent}%)<br/>各班组:<br/>`
    const teams = (shiftTeamMap[params.name] || []).slice().sort((a, b) => b.count - a.count)
    if (teams.length) {
      teams.forEach(t => { html += `　${t.team}: ${t.count} 人次<br/>` })
    } else {
      html += `<span style="color:#909399">　无</span>`
    }
    return html
  })
})

const timeShiftTeamOptions = computed(() => {
  const byTeam = timeShifts.value.by_team || []
  if (!byTeam.length) return {}
  const shiftNames = [...new Set(byTeam.map(s => s.shift_name))]
  const teamMap = {}
  byTeam.forEach(s => {
    if (!teamMap[s.team]) teamMap[s.team] = {}
    teamMap[s.team][s.shift_name] = s.count
  })
  const teams = Object.keys(teamMap)
  return createMultiBarOptions(teams, shiftNames.map(sn => ({
    name: sn,
    data: teams.map(t => teamMap[t][sn] || 0)
  })), '各班组班次结构')
})

const timeUtilizationOptions = computed(() => {
  const data = timeUtilization.value
  if (!data.length) return {}
  const hours = data.map(d => `${d.hour}点`)
  return {
    title: { text: '分时工时利用率', left: 'center', textStyle: { fontSize: 14 } },
    tooltip: {
      trigger: 'axis',
      formatter: (params) => {
        const idx = params[0].dataIndex
        const d = data[idx]
        let html = `<strong>${d.hour}点</strong><br/>`
        params.forEach(p => {
          if (p.value !== null && p.value !== undefined) {
            html += `${p.marker} ${p.seriesName}: ${typeof p.value === 'number' ? p.value.toFixed(1) : p.value}<br/>`
          }
        })
        html += `<span style="color:#909399">应排班: ${d.scheduled_count} 人 · 实际: ${d.actual_count} 人</span>`
        return html
      }
    },
    legend: { data: ['利用率%', '应排班人数', '实际在岗人数'], bottom: 0 },
    grid: { left: '3%', right: '15%', bottom: '15%', containLabel: true },
    xAxis: { type: 'category', data: hours },
    yAxis: [
      { type: 'value', name: '利用率%', max: 100 },
      { type: 'value', name: '人数' }
    ],
    series: [
      { name: '利用率%', type: 'bar', data: data.map(d => d.utilization), itemStyle: { color: CHART_COLORS[0] } },
      { name: '应排班人数', type: 'line', yAxisIndex: 1, data: data.map(d => d.scheduled_count), smooth: true, itemStyle: { color: CHART_COLORS[2] } },
      { name: '实际在岗人数', type: 'line', yAxisIndex: 1, data: data.map(d => d.actual_count), smooth: true, itemStyle: { color: CHART_COLORS[1] } }
    ]
  }
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

function handleTeamTableRowClick(row) {
  handleTeamChartClick({ name: row.team })
}

function handleCheckinRangeClick(params) {
  const bucket = checkinBuckets.value.find(b => b.name === params.name)
  if (!bucket) return
  const range = { min: bucket.min, max: bucket.max }
  if (filterType.value === 'checkin_range' && filterValue.value && filterValue.value.min === range.min && filterValue.value.max === range.max) {
    clearFilter()
  } else {
    filterType.value = 'checkin_range'
    filterValue.value = range
    currentPage.value = 1
  }
}

function handleLateEarlyClick(params) {
  const team = params.name
  const isLate = params.seriesName === '晚签人数'
  const type = isLate ? 'late_team' : 'early_team'
  if (filterType.value === type && filterValue.value === team) {
    clearFilter()
  } else {
    filterType.value = type
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

async function loadTeamLeaders() {
  try {
    const res = await api.get('/employees/leaders')
    const map = {}
    ;(res.data || []).forEach(item => {
      if (item.team) map[item.team] = item.leader
    })
    teamLeaders.value = map
  } catch (e) {
    console.error(e)
  }
}

function buildQueryParams() {
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
  return params
}

async function loadData() {
  try {
    const params = buildQueryParams()
    
    const res = await api.get('/checkins/report', { params })
    
    stats.total_checkins = res.data.stats.total_checkins
    stats.emp_count = res.data.stats.emp_count
    stats.total_hours = res.data.stats.total_hours
    stats.avg_hours = res.data.stats.avg_hours
    stats.overtime_count = res.data.stats.overtime_count || 0
    stats.undertime_count = res.data.stats.undertime_count || 0
    filterType.value = ''
    filterValue.value = ''
    currentPage.value = 1
    tableData.value = res.data.items || []
    loadTeamReport()
    loadTimeAnalysis()
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadTeamReport() {
  try {
    const params = buildQueryParams()
    
    const res = await api.get('/checkins/team-report', { params })
    teamReportData.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载班组报表失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadTimeAnalysis() {
  try {
    const params = buildQueryParams()
    const res = await api.get('/checkins/time-analysis', { params })
    timeHourly.value = res.data.hourly || []
    timeShifts.value = res.data.shifts || { overall: [], by_team: [] }
    timeUtilization.value = res.data.hourly_utilization || []
  } catch (e) {
    ElMessage.error('加载时段分析失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleTimeHourlyClick(params) {
  if (params.componentType !== 'series') return
  const d = timeHourly.value[params.dataIndex]
  if (!d) return
  timeDetailMode.value = 'hour'
  timeDetailTitle.value = `${d.hour}点 签入/签出人员明细`
  timeHourPersons.value = { checkin: [], checkout: [] }
  timeDetailVisible.value = true
  const q = buildQueryParams()
  try {
    const [ci, co] = await Promise.all([
      api.get('/checkins/time-analysis/persons', { params: { ...q, hour: d.hour, type: 'checkin' } }),
      api.get('/checkins/time-analysis/persons', { params: { ...q, hour: d.hour, type: 'checkout' } })
    ])
    timeHourPersons.value = { checkin: ci.data.items || [], checkout: co.data.items || [] }
  } catch (e) {
    ElMessage.error('加载人员明细失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function handleTimeShiftOverallClick(params) {
  if (params.componentType !== 'series') return
  const shiftName = params.name
  timeDetailMode.value = 'shift'
  timeDetailTitle.value = `${shiftName} 班次人员明细`
  timeShiftPersons.value = []
  timeDetailVisible.value = true
  const q = buildQueryParams()
  try {
    const res = await api.get('/checkins/time-analysis/persons', { params: { ...q, shift: shiftName } })
    timeShiftPersons.value = res.data.items || []
  } catch (e) {
    ElMessage.error('加载班次人员失败: ' + (e.response?.data?.detail || e.message))
  }
}

function handleExport() {
  const params = buildQueryParams()
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
  loadTeamLeaders()
  loadData()
  checkinAnnotator.loadAnnotations().then(m => { checkinAnnMap.value = m })
  checkinDetailAnnotator.loadAnnotations().then(m => { checkinDetailAnnMap.value = m })
})
</script>

<style scoped>
.section-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  margin-bottom: 8px;
}
.stats-row {
  margin-bottom: 12px;
  padding: 8px 12px;
  background: #f5f7fa;
  border-radius: 4px;
}
.stats-row :deep(.el-statistic__head) {
  font-size: 12px;
  line-height: 1.2;
  margin-bottom: 2px;
}
.stats-row :deep(.el-statistic__content) {
  font-size: 18px;
  line-height: 1.4;
}
.checkin-report :deep(.echart-container) {
  min-height: 0;
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