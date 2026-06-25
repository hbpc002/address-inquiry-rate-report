<template>
  <div class="reports">
    <el-card>
      <template #header>
        <div class="card-header">
          <span>考勤报表</span>
          <el-space>
            <el-button type="warning" @click="handleRecalculate">重算考勤</el-button>
            <el-button type="success" @click="handleExport">导出报表</el-button>
          </el-space>
        </div>
      </template>

      <el-tabs v-model="activeTab">
        <el-tab-pane label="日报表" name="daily">
          <el-form inline>
            <el-form-item label="日期">
              <el-date-picker v-model="searchDaily.schedule_date" type="date" value-format="YYYY-MM-DD" placeholder="选择日期" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="searchDaily.name" placeholder="姓名" clearable style="width:120px" />
            </el-form-item>
            <el-form-item label="工号">
              <el-input v-model="searchDaily.emp_no" placeholder="工号" clearable style="width:120px" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchDaily.dept" placeholder="全部部门" clearable filterable style="width:180px">
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchDaily.team" placeholder="全部班组" clearable filterable style="width:180px">
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="searchDaily.status" placeholder="全部状态" clearable>
                <el-option label="正常" value="正常" />
                <el-option label="迟到" value="迟到" />
                <el-option label="早退" value="早退" />
                <el-option label="缺勤" value="缺勤" />
                <el-option label="请假" value="请假" />
                <el-option label="公休" value="公休" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadDaily">查询</el-button>
              <el-button @click="resetDaily">重置</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" class="stats-row">
            <el-col :span="3">
              <el-statistic title="应到人数" :value="dailyStats.total" />
            </el-col>
            <el-col :span="3">
              <el-statistic title="出勤人数" :value="dailyStats.attend" />
            </el-col>
            <el-col :span="3">
              <el-statistic title="正常" :value="dailyStats.normal" >
                <template #suffix><span class="stat-normal">人</span></template>
              </el-statistic>
            </el-col>
            <el-col :span="3">
              <el-statistic title="迟到" :value="dailyStats.late" />
            </el-col>
            <el-col :span="3">
              <el-statistic title="缺勤" :value="dailyStats.absent" />
            </el-col>
            <el-col :span="3">
              <el-statistic title="公休" :value="dailyStats.rest" />
            </el-col>
            <el-col :span="3">
              <el-statistic title="出勤率" :value="dailyStats.rate" :precision="1" suffix="%" />
            </el-col>
          </el-row>

          <el-row :gutter="20" v-if="dailyData.length" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="dailyChartOptions" :height="'280px'" @click="handleDailyChartClick" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <div style="margin-bottom: 10px; text-align: center; font-size: 14px; color: #606266">部门出勤对比</div>
                <Echart :options="dailyDeptOptions" :height="'250px'" @click="handleDeptChartClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="dailyData" border stripe show-summary :row-class-name="dailySegmentRowClass">
            <el-table-column prop="schedule_date" label="日期" width="110" />
            <el-table-column prop="emp_no" label="工号" width="110" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="110" />
            <el-table-column prop="dept" label="部门" min-width="130" />
            <el-table-column prop="schedule_type" label="排班类型" width="90" />
            <el-table-column prop="scheduled_hours" label="排班工时" width="90" />
            <el-table-column label="时段" width="70">
              <template #default="{ row }">
                <el-tag v-if="row._totalSegments > 1" size="small" type="info">
                  {{ row._segLabel }}
                </el-tag>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column label="计划时间" width="180">
              <template #default="{ row }">
                {{ row._displayScheduledStart || row.scheduled_start }} - {{ row._displayScheduledEnd || row.scheduled_end }}
              </template>
            </el-table-column>
            <el-table-column prop="actual_checkin" label="实际签到" width="170">
              <template #default="{ row }">
                <span :class="{'text-warning': row._displayLate > 0}">
                  {{ row._displayCheckin || row.actual_checkin?.slice(0, 19) || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column prop="actual_checkout" label="实际签退" width="170">
              <template #default="{ row }">
                <span :class="{'text-warning': row._displayEarly > 0}">
                  {{ row._displayCheckout || row.actual_checkout?.slice(0, 19) || '-' }}
                </span>
              </template>
            </el-table-column>
            <el-table-column label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="getStatusType(row._displayStatus || row.status)">{{ row._displayStatus || row.status }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column label="迟到(分)" width="85">
              <template #default="{ row }">
                {{ row._displayLate ?? row.late_minutes }}
              </template>
            </el-table-column>
            <el-table-column label="早退(分)" width="85">
              <template #default="{ row }">
                {{ row._displayEarly ?? row.early_minutes }}
              </template>
            </el-table-column>
            <el-table-column width="100">
              <template #header>
                实际工时
                <el-tooltip content="仅计算排班时段内的重叠工时" placement="top">
                  <span style="color:#909399;cursor:help;font-size:14px;">ⓘ</span>
                </el-tooltip>
              </template>
              <template #default="{ row }">
                {{ row._displayActualHours ?? row.actual_hours }}
              </template>
            </el-table-column>
          </el-table>
          <el-pagination
            v-if="dailyPagination.total > dailyPagination.limit"
            v-model:current-page="dailyPagination.page"
            v-model:page-size="dailyPagination.limit"
            :total="dailyPagination.total"
            layout="total, prev, pager, next"
            @current-change="loadDaily"
            style="margin-top: 15px"
          />
        </el-tab-pane>

        <el-tab-pane label="月度汇总" name="month">
          <el-form inline>
            <el-form-item label="月份">
              <el-date-picker v-model="searchMonthly.year_month" type="month" value-format="YYYY-MM" placeholder="选择月份" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="searchMonthly.name" placeholder="姓名" clearable style="width:120px" />
            </el-form-item>
            <el-form-item label="工号">
              <el-input v-model="searchMonthly.emp_no" placeholder="工号" clearable style="width:120px" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchMonthly.dept" placeholder="全部部门" clearable filterable style="width:180px">
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchMonthly.team" placeholder="全部班组" clearable filterable style="width:180px">
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadMonthly">查询</el-button>
              <el-button @click="resetMonthly">重置</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" class="stats-row">
            <el-col :span="4">
              <el-statistic title="员工人数" :value="monthlyStats.total" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="计划工时" :value="monthlyStats.scheduled" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="实际工时" :value="monthlyStats.actual" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="加班工时" :value="monthlyStats.overtime" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="欠时工时" :value="monthlyStats.owed" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="出勤天数" :value="monthlyStats.workDays" :precision="0" />
            </el-col>
          </el-row>

          <el-row :gutter="20" v-if="monthlyData.length" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-card shadow="hover">
                <div style="margin-bottom: 10px; display: flex; justify-content: space-between; align-items: center">
                  <span style="font-size: 14px; color: #606266">部门工时对比</span>
                  <el-radio-group v-model="currentChartType" size="small">
                    <el-radio-button value="bar">柱状图</el-radio-button>
                    <el-radio-button value="line">折线图</el-radio-button>
                  </el-radio-group>
                </div>
                <Echart :options="monthlyDeptOptions" :height="'250px'" @click="handleDeptChartClick" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="monthlyOvertimeOptions" :height="'280px'" @click="handleOvertimeChartClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="monthlyData" border stripe show-summary>
            <el-table-column prop="emp_no" label="工号" width="110" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="110" />
            <el-table-column prop="dept" label="部门" min-width="130" />
            <el-table-column prop="scheduled_hours" label="计划工时" width="90" sortable />
            <el-table-column prop="actual_hours" label="实际工时" width="90" sortable />
            <el-table-column prop="overtime_hours" label="加班" width="75" sortable>
              <template #default="{ row }">
                <span :class="{'text-success': row.overtime_hours > 0}">{{ row.overtime_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="owed_hours" label="欠时" width="75" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.owed_hours > 0}">{{ row.owed_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="normal_days" label="正常" width="65" sortable />
            <el-table-column prop="late_days" label="迟到" width="65" sortable>
              <template #default="{ row }">
                <span :class="{'text-warning': row.late_days > 0}">{{ row.late_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="early_days" label="早退" width="65" sortable />
            <el-table-column prop="absent_days" label="缺勤" width="65" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.absent_days > 0}">{{ row.absent_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="leave_days" label="请假" width="65" />
            <el-table-column prop="timeoff_days" label="公休" width="65" />
          </el-table>
          <el-pagination
            v-if="monthlyPagination.total > monthlyPagination.limit"
            v-model:current-page="monthlyPagination.page"
            v-model:page-size="monthlyPagination.limit"
            :total="monthlyPagination.total"
            layout="total, prev, pager, next"
            @current-change="loadMonthly"
            style="margin-top: 15px"
          />
        </el-tab-pane>

        <el-tab-pane label="自定义时间段" name="daterange">
          <el-form inline>
            <el-form-item label="开始日期">
              <el-date-picker v-model="searchRange.start_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="结束日期">
              <el-date-picker v-model="searchRange.end_date" type="date" value-format="YYYY-MM-DD" />
            </el-form-item>
            <el-form-item label="姓名">
              <el-input v-model="searchRange.name" placeholder="姓名" clearable style="width:120px" />
            </el-form-item>
            <el-form-item label="工号">
              <el-input v-model="searchRange.emp_no" placeholder="工号" clearable style="width:120px" />
            </el-form-item>
            <el-form-item label="部门">
              <el-select v-model="searchRange.dept" placeholder="全部部门" clearable filterable style="width:180px">
                <el-option v-for="d in depts" :key="d.dept" :label="d.dept" :value="d.dept" />
              </el-select>
            </el-form-item>
            <el-form-item label="班组">
              <el-select v-model="searchRange.team" placeholder="全部班组" clearable filterable style="width:180px">
                <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
              </el-select>
            </el-form-item>
            <el-form-item label="状态">
              <el-select v-model="searchRange.status" placeholder="全部状态" clearable style="width:180px">
                <el-option label="正常" value="正常" />
                <el-option label="迟到" value="迟到" />
                <el-option label="早退" value="早退" />
                <el-option label="缺勤" value="缺勤" />
              </el-select>
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadRange">查询</el-button>
              <el-button @click="resetRange">重置</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" class="stats-row">
            <el-col :span="4">
              <el-statistic title="员工人数" :value="rangeStats.total" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总计划工时" :value="rangeStats.scheduled" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总实际工时" :value="rangeStats.actual" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总加班" :value="rangeStats.overtime" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总欠时" :value="rangeStats.owed" :precision="1" />
            </el-col>
            <el-col :span="4">
              <el-statistic title="总出勤天数" :value="rangeStats.workDays" :precision="0" />
            </el-col>
          </el-row>

          <el-row :gutter="20" v-if="rangeData.length" style="margin-bottom: 20px">
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="rangeDeptOptions" :height="'280px'" @click="handleDeptChartClick" />
              </el-card>
            </el-col>
            <el-col :span="12">
              <el-card shadow="hover">
                <Echart :options="rangeStatusOptions" :height="'280px'" @click="handleRangeStatusClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="rangeData" border stripe show-summary>
            <el-table-column prop="emp_no" label="工号" width="110" />
            <el-table-column prop="name" label="姓名" width="100" />
            <el-table-column prop="team" label="班组" width="110" />
            <el-table-column prop="dept" label="部门" min-width="130" />
            <el-table-column prop="scheduled_hours" label="计划工时" width="90" sortable />
            <el-table-column prop="actual_hours" label="实际工时" width="90" sortable />
            <el-table-column prop="overtime_hours" label="加班" width="75" sortable>
              <template #default="{ row }">
                <span :class="{'text-success': row.overtime_hours > 0}">{{ row.overtime_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="owed_hours" label="欠时" width="75" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.owed_hours > 0}">{{ row.owed_hours }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="normal_days" label="正常" width="65" sortable />
            <el-table-column prop="late_days" label="迟到" width="65" sortable>
              <template #default="{ row }">
                <span :class="{'text-warning': row.late_days > 0}">{{ row.late_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="early_days" label="早退" width="65" sortable />
            <el-table-column prop="absent_days" label="缺勤" width="65" sortable>
              <template #default="{ row }">
                <span :class="{'text-danger': row.absent_days > 0}">{{ row.absent_days }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="leave_days" label="请假" width="65" />
            <el-table-column prop="timeoff_days" label="公休" width="65" />
            <el-table-column prop="work_days" label="出勤天数" width="85" sortable />
          </el-table>
          <el-pagination
            v-if="rangePagination.total > rangePagination.limit"
            v-model:current-page="rangePagination.page"
            v-model:page-size="rangePagination.limit"
            :total="rangePagination.total"
            layout="total, prev, pager, next"
            @current-change="loadRange"
            style="margin-top: 15px"
          />
        </el-tab-pane>

        <el-tab-pane label="班组排名" name="ranking">
          <el-form inline>
            <el-form-item label="月份">
              <el-date-picker v-model="searchRank.year_month" type="month" value-format="YYYY-MM" />
            </el-form-item>
            <el-form-item>
              <el-button type="primary" @click="loadRanking">查询</el-button>
            </el-form-item>
          </el-form>

          <el-row :gutter="20" v-if="rankingData.length" style="margin-bottom: 20px">
            <el-col :span="24">
              <el-card shadow="hover">
                <Echart :options="rankingChartOptions" :height="'300px'" @click="handleRankingChartClick" />
              </el-card>
            </el-col>
          </el-row>

          <el-table :data="rankingData" border stripe>
            <el-table-column type="index" label="排名" width="60" />
            <el-table-column prop="team" label="班组" width="150" />
            <el-table-column prop="emp_count" label="人数" width="80" sortable />
            <el-table-column prop="total_scheduled" label="计划工时" width="100" sortable />
            <el-table-column prop="total_actual" label="实际工时" width="100" sortable />
            <el-table-column prop="total_overtime" label="加班工时" width="100" sortable />
            <el-table-column prop="avg_attendance" label="平均出勤率" width="110" sortable>
              <template #default="{ row }">
                {{ (row.avg_attendance * 100).toFixed(1) }}%
              </template>
            </el-table-column>
            <el-table-column prop="late_count" label="迟到次数" width="90" sortable />
            <el-table-column prop="absent_count" label="缺勤次数" width="90" sortable />
          </el-table>
        </el-tab-pane>
      </el-tabs>
    </el-card>

    <el-dialog v-model="exportDialogVisible" title="导出报表" width="400px">
      <el-form :model="exportForm" label-width="80px">
        <el-form-item label="报表类型">
          <el-select v-model="exportForm.type">
            <el-option label="日报表" value="daily" />
            <el-option label="月报表" value="month" />
            <el-option label="时间段" value="date_range" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="exportForm.type === 'daily'" label="日期">
          <el-date-picker v-model="exportForm.schedule_date" type="date" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item v-if="exportForm.type === 'month'" label="月份">
          <el-date-picker v-model="exportForm.year_month" type="month" value-format="YYYY-MM" />
        </el-form-item>
        <el-form-item v-if="exportForm.type === 'date_range'" label="日期范围">
          <el-date-picker v-model="exportForm.dateRange" type="daterange" value-format="YYYY-MM-DD" />
        </el-form-item>
        <el-form-item label="班组">
          <el-select v-model="exportForm.team" clearable placeholder="全部">
            <el-option v-for="t in teams" :key="t.team" :label="t.team" :value="t.team" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="exportDialogVisible = false">取消</el-button>
        <el-button type="primary" @click="confirmExport">确定导出</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="recalculateDialogVisible" title="重算考勤" width="420px">
      <el-form label-width="80px">
        <el-form-item label="开始日期">
          <el-date-picker v-model="recalculateRange.start" type="date" value-format="YYYY-MM-DD" placeholder="选择开始日期" />
        </el-form-item>
        <el-form-item label="结束日期">
          <el-date-picker v-model="recalculateRange.end" type="date" value-format="YYYY-MM-DD" placeholder="选择结束日期" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="recalculateDialogVisible = false">取消</el-button>
        <el-button type="warning" :loading="recalculating" @click="confirmRecalculate">开始重算</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="detailDialogVisible" :title="detailTitle" width="800px">
      <el-table :data="detailData" border stripe max-height="400" v-if="detailData.length">
        <el-table-column prop="emp_no" label="工号" width="100" />
        <el-table-column prop="name" label="姓名" width="100" />
        <el-table-column prop="team" label="班组" width="120" />
        <el-table-column prop="dept" label="部门" width="120" />
        <el-table-column prop="schedule_date" label="日期" width="120" v-if="activeTab === 'daily' || activeTab === 'daterange'" />
        <el-table-column prop="status" label="状态" width="80" v-if="activeTab !== 'month'">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="actual_hours" label="实际工时" width="90" v-if="activeTab === 'month' || activeTab === 'daterange'" />
        <el-table-column prop="overtime_hours" label="加班" width="70" v-if="activeTab === 'month' || activeTab === 'daterange'">
          <template #default="{ row }">
            <span :class="{'text-success': row.overtime_hours > 0}">{{ row.overtime_hours }}</span>
          </template>
        </el-table-column>
        <el-table-column prop="owed_hours" label="欠时" width="70" v-if="activeTab === 'month' || activeTab === 'daterange'">
          <template #default="{ row }">
            <span :class="{'text-danger': row.owed_hours > 0}">{{ row.owed_hours }}</span>
          </template>
        </el-table-column>
      </el-table>
      <el-empty v-if="!detailData.length" description="暂无数据" />
      <template #footer>
        <el-button @click="detailDialogVisible = false">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted, computed, watch } from 'vue'
import { api } from '../stores/user'
import { ElMessage } from 'element-plus'
import Echart from '../components/Echart.vue'
import { createPieOptions, createBarOptions, createLineOptions, createHorizontalBarOptions, createMultiBarOptions } from '../utils/echarts'
import { getYesterday } from '../utils/date'
import { usePersistedFilters } from '../composables/usePersistedFilters'

const savedTab = sessionStorage.getItem('reports-active-tab')
const activeTab = ref(savedTab || 'daily')
watch(activeTab, (val) => {
  sessionStorage.setItem('reports-active-tab', val)
})
const dailyData = ref([])
const dailyAllData = ref([])
const monthlyData = ref([])
const monthlyAllData = ref([])
const rangeData = ref([])
const rangeAllData = ref([])
const rankingData = ref([])
const teams = ref([])
const depts = ref([])

const dailyStats = reactive({ total: 0, attend: 0, normal: 0, late: 0, absent: 0, rest: 0, rate: 0 })
const monthlyStats = reactive({ total: 0, scheduled: 0, actual: 0, overtime: 0, owed: 0, workDays: 0 })
const rangeStats = reactive({ total: 0, scheduled: 0, actual: 0, overtime: 0, owed: 0, workDays: 0 })

const dailyPagination = reactive({ page: 1, limit: 20, total: 0 })
const monthlyPagination = reactive({ page: 1, limit: 20, total: 0 })
const rangePagination = reactive({ page: 1, limit: 20, total: 0 })

const { filters: searchDaily, resetFilters: resetDailyFilters } = usePersistedFilters(
  'reports-daily',
  { schedule_date: getYesterday(), name: '', emp_no: '', dept: '', team: '', status: '' }
)
const { filters: searchMonthly, resetFilters: resetMonthlyFilters } = usePersistedFilters(
  'reports-monthly',
  { year_month: new Date().toISOString().slice(0, 7), name: '', emp_no: '', dept: '', team: '' }
)
const { filters: searchRange, resetFilters: resetRangeFilters } = usePersistedFilters(
  'reports-range',
  { start_date: new Date(new Date().getFullYear(), new Date().getMonth(), 1).toISOString().slice(0, 10), end_date: getYesterday(), name: '', emp_no: '', dept: '', team: '', status: '' }
)
const { filters: searchRank, resetFilters: resetRankFilters } = usePersistedFilters(
  'reports-rank',
  { year_month: new Date().toISOString().slice(0, 7) }
)

const exportDialogVisible = ref(false)
const exportForm = reactive({ type: 'month', schedule_date: '', year_month: '', dateRange: [], team: '' })

const recalculateDialogVisible = ref(false)
const recalculating = ref(false)
const recalculateRange = reactive({ start: '', end: '' })

const currentChartType = ref('bar')
const detailDialogVisible = ref(false)
const detailTitle = ref('')
const detailData = ref([])

const dailyChartOptions = computed(() => {
  if (!dailyAllData.value.length) return {}
  const seen = new Set()
  const statusCount = {}
  dailyAllData.value.forEach(d => {
    if (seen.has(d.emp_id)) return
    seen.add(d.emp_id)
    statusCount[d.status] = (statusCount[d.status] || 0) + 1
  })
  const pieData = Object.entries(statusCount).map(([name, value]) => ({ name, value }))
  return createPieOptions(pieData, '考勤状态分布')
})

const dailyDeptOptions = computed(() => {
  if (!dailyAllData.value.length) return {}
  const seen = new Set()
  const deptMap = {}
  dailyAllData.value.forEach(d => {
    if (seen.has(d.emp_id)) return
    seen.add(d.emp_id)
    if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
    deptMap[d.dept].scheduled += d.scheduled_hours || 0
    deptMap[d.dept].actual += d.actual_hours || 0
  })
  const depts = Object.keys(deptMap).slice(0, 8)
  return createMultiBarOptions(depts, [
    { name: '计划工时', data: depts.map(d => Math.round(deptMap[d].scheduled)) },
    { name: '实际工时', data: depts.map(d => Math.round(deptMap[d].actual)) }
  ], '部门工时对比')
})

const monthlyDeptOptions = computed(() => {
  if (!monthlyAllData.value.length) return {}
  const deptMap = {}
  monthlyAllData.value.forEach(d => {
    if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
    deptMap[d.dept].scheduled += d.scheduled_hours || 0
    deptMap[d.dept].actual += d.actual_hours || 0
  })
  const depts = Object.keys(deptMap).slice(0, 8)
  if (currentChartType.value === 'line') {
    return createLineOptions(depts, depts.map(d => Math.round(deptMap[d].actual)), '部门工时趋势', '部门', '实际工时')
  }
  return createMultiBarOptions(depts, [
    { name: '计划工时', data: depts.map(d => Math.round(deptMap[d].scheduled)) },
    { name: '实际工时', data: depts.map(d => Math.round(deptMap[d].actual)) }
  ], '部门工时对比')
})

const monthlyOvertimeOptions = computed(() => {
  if (!monthlyAllData.value.length) return {}
  const overtime = monthlyAllData.value.filter(d => d.overtime_hours > 0).length
  const owed = monthlyAllData.value.filter(d => d.owed_hours > 0).length
  const normal = monthlyAllData.value.length - overtime - owed
  return createPieOptions([
    { name: '正常', value: normal },
    { name: '加班', value: overtime },
    { name: '欠时', value: owed }
  ], '加班/欠时分布', ['#67c23a', '#e6a23c', '#f56c6c'])
})

const rangeDeptOptions = computed(() => {
  if (!rangeAllData.value.length) return {}
  const deptMap = {}
  rangeAllData.value.forEach(d => {
    if (!deptMap[d.dept]) deptMap[d.dept] = { scheduled: 0, actual: 0 }
    deptMap[d.dept].scheduled += d.scheduled_hours || 0
    deptMap[d.dept].actual += d.actual_hours || 0
  })
  const depts = Object.keys(deptMap).slice(0, 8)
  if (currentChartType.value === 'line') {
    return createLineOptions(depts, depts.map(d => Math.round(deptMap[d].actual)), '部门工时趋势', '部门', '实际工时')
  }
  return createMultiBarOptions(depts, [
    { name: '计划工时', data: depts.map(d => Math.round(deptMap[d].scheduled)) },
    { name: '实际工时', data: depts.map(d => Math.round(deptMap[d].actual)) }
  ], '部门工时对比')
})

const rangeStatusOptions = computed(() => {
  if (!rangeAllData.value.length) return {}
  const statusCount = {}
  rangeAllData.value.forEach(d => {
    for (const [key, label] of [['normal_days', '正常'], ['late_days', '迟到'], ['early_days', '早退'], ['absent_days', '缺勤'], ['leave_days', '请假'], ['timeoff_days', '公休']]) {
      const v = d[key] || 0
      if (v > 0) statusCount[label] = (statusCount[label] || 0) + v
    }
  })
  const data = Object.entries(statusCount).map(([name, value]) => ({ name, value }))
  return createPieOptions(data, '异常考勤分布')
})

const rankingChartOptions = computed(() => {
  if (!rankingData.value.length) return {}
  const data = [...rankingData.value].sort((a, b) => b.avg_attendance - a.avg_attendance).slice(0, 8)
  return createHorizontalBarOptions(data.map(d => d.team), data.map(d => Math.round(d.avg_attendance * 100)), '', '班组', '出勤率(%)')
})

function getStatusType(status) {
  const map = { '正常': 'success', '迟到': 'warning', '早退': 'warning', '缺勤': 'danger', '请假': 'info', '公休': '' }
  return map[status] || 'info'
}

function calcDailyStats(data) {
  const seen = new Set()
  const unique = data.filter(d => {
    if (seen.has(d.emp_id)) return false
    seen.add(d.emp_id)
    return true
  })
  dailyStats.total = unique.filter(d => d.status !== '公休').length
  dailyStats.attend = unique.filter(d => d.status !== '缺勤' && d.status !== '公休').length
  dailyStats.normal = unique.filter(d => d.status === '正常').length
  dailyStats.late = unique.filter(d => d.status === '迟到').length
  dailyStats.absent = unique.filter(d => d.status === '缺勤').length
  dailyStats.rest = unique.filter(d => d.status === '公休').length
  dailyStats.rate = dailyStats.total ? Math.round(dailyStats.attend / dailyStats.total * 100) : 0
}

function calcMonthlyStats(data) {
  monthlyStats.total = data.length
  monthlyStats.scheduled = data.reduce((s, d) => s + (d.scheduled_hours || 0), 0)
  monthlyStats.actual = data.reduce((s, d) => s + (d.actual_hours || 0), 0)
  monthlyStats.overtime = data.reduce((s, d) => s + (d.overtime_hours || 0), 0)
  monthlyStats.owed = data.reduce((s, d) => s + (d.owed_hours || 0), 0)
  monthlyStats.workDays = data.reduce((s, d) => s + (d.normal_days || 0), 0)
}

function calcRangeStats(data) {
  rangeStats.total = data.length
  rangeStats.scheduled = data.reduce((s, d) => s + (d.scheduled_hours || 0), 0)
  rangeStats.actual = data.reduce((s, d) => s + (d.actual_hours || 0), 0)
  rangeStats.overtime = data.reduce((s, d) => s + (d.overtime_hours || 0), 0)
  rangeStats.owed = data.reduce((s, d) => s + (d.owed_hours || 0), 0)
  rangeStats.workDays = data.reduce((s, d) => s + (d.work_days || 0), 0)
}

function expandItems(items) {
  const expanded = []
  for (const item of items) {
    const segs = item.segment_details || []
    if (segs.length <= 1) {
      expanded.push({ ...item, _totalSegments: 1, _segLabel: '', _displayScheduledStart: null, _displayScheduledEnd: null, _displayCheckin: null, _displayCheckout: null, _displayLate: null, _displayEarly: null, _displayActualHours: null, _displayStatus: null })
    } else {
      segs.forEach((seg, i) => {
        expanded.push({
          ...item,
          _totalSegments: segs.length,
          _segLabel: `${i + 1}/${segs.length}`,
          _displayScheduledStart: seg.start,
          _displayScheduledEnd: seg.end,
          _displayCheckin: seg.actual_checkin ? seg.actual_checkin.slice(0, 19) : '-',
          _displayCheckout: seg.actual_checkout ? seg.actual_checkout.slice(0, 19) : '-',
          _displayLate: seg.late_minutes,
          _displayEarly: seg.early_minutes,
          _displayActualHours: seg.actual_hours,
          _displayStatus: seg.status
        })
      })
    }
  }
  return expanded
}

async function loadDaily() {
  if (!searchDaily.schedule_date) {
    searchDaily.schedule_date = getYesterday()
  }
  try {
    const res = await api.get('/reports/daily', { params: { ...searchDaily, page: dailyPagination.page, limit: dailyPagination.limit } })
    dailyData.value = expandItems(res.data.items || [])
    dailyPagination.total = res.data.total || 0

    const allRes = await api.get('/reports/daily', { params: { ...searchDaily, page: 1, limit: 200 } })
    const allExpanded = expandItems(allRes.data.items || [])
    dailyAllData.value = allExpanded
    calcDailyStats(allExpanded)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

function dailySegmentRowClass({ row }) {
  return row._totalSegments > 1 ? 'segment-sub-row' : ''
}

async function loadMonthly() {
  if (!searchMonthly.year_month) {
    searchMonthly.year_month = new Date().toISOString().slice(0, 7)
  }
  try {
    const res = await api.get('/reports/month-summary', { params: { ...searchMonthly, page: monthlyPagination.page, limit: monthlyPagination.limit } })
    monthlyData.value = res.data.items || []
    monthlyPagination.total = res.data.total || 0

    const allRes = await api.get('/reports/month-summary', { params: { ...searchMonthly, page: 1, limit: 200 } })
    monthlyAllData.value = allRes.data.items || []
    calcMonthlyStats(monthlyAllData.value)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadRange() {
  if (!searchRange.start_date || !searchRange.end_date) {
    ElMessage.warning('请选择开始和结束日期')
    return
  }
  try {
    const res = await api.get('/reports/date-range', { params: { ...searchRange, page: rangePagination.page, limit: rangePagination.limit } })
    rangeData.value = res.data.items || []
    rangePagination.total = res.data.total || 0

    const allRes = await api.get('/reports/date-range', { params: { ...searchRange, page: 1, limit: 200 } })
    rangeAllData.value = allRes.data.items || []
    calcRangeStats(rangeAllData.value)
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

async function loadRanking() {
  if (!searchRank.year_month) {
    searchRank.year_month = new Date().toISOString().slice(0, 7)
  }
  try {
    const res = await api.get('/reports/team-ranking', { params: { year_month: searchRank.year_month } })
    rankingData.value = res.data || []
  } catch (e) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
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

async function loadDepts() {
  try {
    const res = await api.get('/checkins/departments')
    depts.value = res.data || []
  } catch (e) {
    console.error(e)
  }
}

function resetDaily() {
  resetDailyFilters()
  dailyPagination.page = 1
  loadDaily()
}

function resetMonthly() {
  resetMonthlyFilters()
  monthlyPagination.page = 1
  loadMonthly()
}

function resetRange() {
  resetRangeFilters()
  rangePagination.page = 1
  loadRange()
}

function handleExport() {
  exportForm.type = 'month'
  exportForm.year_month = new Date().toISOString().slice(0, 7)
  exportForm.team = ''
  exportDialogVisible.value = true
}

function confirmExport() {
  const params = new URLSearchParams()
  params.append('type', exportForm.type)
  if (exportForm.team) params.append('team', exportForm.team)

  if (exportForm.type === 'daily' && exportForm.schedule_date) {
    params.append('schedule_date', exportForm.schedule_date)
  } else if (exportForm.type === 'month' && exportForm.year_month) {
    params.append('year_month', exportForm.year_month)
  } else if (exportForm.type === 'date_range' && exportForm.dateRange?.length === 2) {
    params.append('start_date', exportForm.dateRange[0])
    params.append('end_date', exportForm.dateRange[1])
  }

  const url = `${import.meta.env.VITE_API_BASE_URL || '/api'}/reports/export?${params}`
  window.open(url, '_blank')
  exportDialogVisible.value = false
  ElMessage.success('导出成功')
}

function handleRecalculate() {
  recalculateRange.start = ''
  recalculateRange.end = ''
  recalculateDialogVisible.value = true
}

async function confirmRecalculate() {
  if (!recalculateRange.start || !recalculateRange.end) {
    ElMessage.warning('请选择开始和结束日期')
    return
  }
  recalculating.value = true
  try {
    await api.post('/reports/recalculate', null, {
      params: { start_date: recalculateRange.start, end_date: recalculateRange.end }
    })
    ElMessage.success('重算完成')
    recalculateDialogVisible.value = false
    loadDaily()
    loadMonthly()
  } catch (e) {
    ElMessage.error('重算失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    recalculating.value = false
  }
}

function handleDailyChartClick(params) {
  const status = params.name
  const filtered = dailyData.value.filter(d => d.status === status)
  detailTitle.value = `${status}人员列表 (${filtered.length}人)`
  detailData.value = filtered
  detailDialogVisible.value = true
}

function handleDeptChartClick(params) {
  const deptName = params.name
  let data = []
  if (activeTab.value === 'month') {
    data = monthlyData.value.filter(d => d.dept === deptName)
  } else if (activeTab.value === 'daterange') {
    data = rangeData.value.filter(d => d.dept === deptName)
  } else if (activeTab.value === 'daily') {
    data = dailyData.value.filter(d => d.dept === deptName)
  }
  detailTitle.value = `${deptName}员工列表 (${data.length}人)`
  detailData.value = data
  detailDialogVisible.value = true
}

function handleOvertimeChartClick(params) {
  const type = params.name
  let data = []
  if (type === '加班') {
    data = monthlyData.value.filter(d => d.overtime_hours > 0)
  } else if (type === '欠时') {
    data = monthlyData.value.filter(d => d.owed_hours > 0)
  } else {
    data = monthlyData.value.filter(d => d.overtime_hours <= 0 && d.owed_hours <= 0)
  }
  detailTitle.value = `${type}人员列表 (${data.length}人)`
  detailData.value = data
  detailDialogVisible.value = true
}

function handleRangeStatusClick(params) {
  const status = params.name
  const filtered = rangeData.value.filter(d => d.status === status)
  detailTitle.value = `${status}人员列表 (${filtered.length}人)`
  detailData.value = filtered
  detailDialogVisible.value = true
}

function handleRankingChartClick(params) {
  const teamName = params.name
  const teamData = rankingData.value.find(r => r.team === teamName)
  if (teamData) {
    detailTitle.value = `${teamName} - 排名${rankingData.value.sort((a, b) => b.avg_attendance - a.avg_attendance).findIndex(r => r.team === teamName) + 1} (${teamData.emp_count}人, 出勤率${Math.round(teamData.avg_attendance * 100)}%)`
    detailData.value = []
  }
  detailDialogVisible.value = true
}

onMounted(() => {
  loadTeams()
  loadDepts()
  loadDaily()
})
</script>

<style scoped>
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.stats-row {
  margin-bottom: 20px;
  padding: 15px;
  background: #f5f7fa;
  border-radius: 4px;
}

.text-success { color: #67c23a; font-weight: bold; }
.text-warning { color: #e6a23c; }
.text-danger { color: #f56c6c; font-weight: bold; }

.stat-normal { color: #67c23a; }
</style>