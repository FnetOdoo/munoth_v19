from odoo import models, fields, api, _
from datetime import date, time, datetime

# model_ref = {'anode_slitting': 'anode.slitting',
#              'cathode_slitting': 'cathode.slitting ',
#              'anode_drying': 'anode.drying',
#              'cathode_drying': 'cathode.drying',
#              'diaphragm_drying': 'dia.drying',
#              'anode_electrode_making': 'anode.electrode.making',
#              'cathode_electrode_making': 'cathode.electrode.making',
#              'winding': 'winding',
#              'hot_press_jelly': 'hot.press.jelly',
#              'assembly': 'assembly.cell',
#              'cell_drying': 'cell.drying',
#              'injection': 'cell.injection',
#              'high_temperature': 'high.temperature.cell',
#              'cell_clamp_baking': 'cell.clamp.baking',
#              'aged_formation_cell': 'aged.formation.cell',
#              'degas': 'degas.cell', 'dsf': 'double.side.folding',
#              'pad_printing': 'pad.printing',
#              'capacity_test': 'capacity.test',
#              'voltage_test': 'voltage.test',
#              'aged_formation_cell_2': 'aged.formation.cell',
#              'voltage_test_2': 'voltage.test',
#              'packing': 'package.move',
#              'powerbank': 'mrp.powerbank',
#              'qr_code_print': 'qr.code.printing',
#              }


class MonthlyPlan(models.Model):
    _name = "monthly.plan"
    _description = 'Production Monthly Plan'

    name = fields.Char('Reference', copy=False, readonly=True, default=lambda x: _('New'))
    state = fields.Selection([('draft', 'Draft'), ('confirm', 'Confirmed'), ('cancel', 'Cancelled')], default='draft',
                             string="Status", tracking=True)
    date = fields.Date('Date', default=fields.Date.today, required=True)
    model_id = fields.Many2one('product.model', string="Model", required=1)
    # stage = fields.Selection([
    #     ('stage_0', 'Process Type 0'),
    #     ('stage_1', 'Process Type 1'),
    #     ('stage_2', 'Process Type 2'),
    #     ('stage_3', 'Process Type 3'),
    #     ('stage_4', 'Process Type 4'),
    #     ('stage_5', 'Process Type 5'),
    #     ('stage_6', 'Process Type 6')], default='stage_1', help='Choose stage of going to production', string="Stage",
    #     required=1)
    manufacturing_stages_id = fields.Many2one('manufacturing.stages')

    user_id = fields.Many2one('res.users', 'Responsible', default=lambda self: self.env.user,
                              states={'confirm': [('readonly', True)], 'cancel': [('readonly', True)]})
    resource_calendar_id = fields.Many2one('resource.calendar', 'Working Hours',
                                           default=lambda self: self.env.company.resource_calendar_id,
                                           domain="['|', ('company_id', '=', False), ('company_id', '=', company_id)]",
                                           help="Working hours used to determine the weekends and public holidays.")
    line_ids = fields.One2many('monthly.plan.line', 'plan_id', string="Daily Plan")
    company_id = fields.Many2one(
        'res.company', 'Company', index=True,
        default=lambda self: self.env.company)

    @api.onchange('manufacturing_stages_id')
    def onchange_stage(self):
        self.line_ids = False
        lines = []
        for operation in self.model_id.operation_ids.filtered(lambda x: x.manufacturing_stages_id == self.manufacturing_stages_id).sorted(
                key=lambda x: x.sequence):
            lines.append(
                (0, 0, {'operation_id': operation.id, 'month': self.date.month or '', 'year': self.date.year or ''}))
        self.line_ids = lines

    def action_confirm(self):
        for rec in self:
            rec.write({'state': 'confirm'})

    def action_cancel(self):
        for rec in self:
            rec.write({'state': 'cancel'})

    def action_reset(self):
        for rec in self:
            rec.write({'state': 'draft'})

    def action_view_report(self):
        self.env['monthly.plan.result'].search([('plan_id', '=', self.id)]).unlink()
        for line in self.line_ids:
            for day in range(1, 31):
                current_date = datetime.combine(fields.Date.from_string(self.date.replace(day=day)), time.min)
                current_date_end = datetime.combine(fields.Date.from_string(self.date.replace(day=day)), time.max)

                record = self.env['manufacturing.process'].search([
                    ('manufacturing_process_type_id', '=', line.operation_id.manufacturing_process_type_id.id),
                    ('start_time', '>=', current_date),
                    ('start_time', '<=', current_date_end),
                ])

                rejected = self.env['mrp.quality'].search([
                    ('operation_id', '=', line.operation_id.id),
                    ('state', '=', 'done'),
                    ('date', '>=', current_date),
                    ('date', '<=', current_date_end),
                ])

                self.env['monthly.plan.result'].create({
                    'plan_id': self.id,
                    'date': current_date.date(),
                    'operation_id': line.operation_id.id,
                    'planned_qty': line['day_' + str(day)],
                    'produced_qty': sum(record.mapped('finished_move_ids').mapped('quantity')),
                    'rejected_qty': sum(rejected.mapped('quantity')),
                })

        return {
            'name': _('Result for the Month of %s/%s' % (self.date.month, self.date.year)),
            'type': 'ir.actions.act_window',
            'view_mode': 'list',
            'res_model': 'monthly.plan.result',
            'domain': [('plan_id', '=', self.id)],
            'context': {'group_by': ['date:week', 'date:day']}
        }


class MonthlyPlanLine(models.Model):
    _name = 'monthly.plan.line'
    _description = 'Monthly Plan Line'

    @api.depends('date')
    def compute_month(self):
        for rec in self:
            rec.month = str(rec.plan_id.date.month or '')
            rec.year = (rec.plan_id.date.year or '')

    @api.depends('date', 'plan_id.date')
    def compute_opening(self):
        for rec in self:
            # entries = self.env['']
            rec.opening_qty = 1

    plan_id = fields.Many2one('monthly.plan', string="Monthly Plan")
    date = fields.Date('Date')
    operation_id = fields.Many2one('manufacturing.operation', string="Process")
    month = fields.Char('Month', compute='compute_month')
    year = fields.Char('Year', compute='compute_month')
    opening_qty = fields.Integer('Opening', compute='compute_opening')
    day_1 = fields.Integer('1')
    day_2 = fields.Integer('2')
    day_3 = fields.Integer('3')
    day_4 = fields.Integer('4')
    day_5 = fields.Integer('5')
    day_6 = fields.Integer('6')
    day_7 = fields.Integer('7')
    day_8 = fields.Integer('8')
    day_9 = fields.Integer('9')
    day_10 = fields.Integer('10')
    day_11 = fields.Integer('11')
    day_12 = fields.Integer('12')
    day_13 = fields.Integer('14')
    day_14 = fields.Integer('14')
    day_15 = fields.Integer('15')
    day_16 = fields.Integer('16')
    day_17 = fields.Integer('17')
    day_18 = fields.Integer('18')
    day_19 = fields.Integer('19')
    day_20 = fields.Integer('20')
    day_21 = fields.Integer('21')
    day_22 = fields.Integer('22')
    day_23 = fields.Integer('23')
    day_24 = fields.Integer('24')
    day_25 = fields.Integer('25')
    day_26 = fields.Integer('26')
    day_27 = fields.Integer('27')
    day_28 = fields.Integer('28')
    day_29 = fields.Integer('29')
    day_30 = fields.Integer('30')
    day_31 = fields.Integer('31')


class MonthlyPlanResult(models.TransientModel):
    _name = 'monthly.plan.result'
    _description = 'Monthly Plan Result'

    plan_id = fields.Many2one('monthly.plan', string="Monthly Plan")
    date = fields.Date('Date')
    operation_id = fields.Many2one('manufacturing.operation', string="Process")
    planned_qty = fields.Integer("Plan")
    produced_qty = fields.Integer("Produced")
    rejected_qty = fields.Integer("Rejected")
