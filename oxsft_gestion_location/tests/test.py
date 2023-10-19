# -*- coding: utf-8 -*-
from odoo.tests.common import TransactionCase

class TestTodo(TransactionCase):
    def test_create(self):
        Todo = self.env['fleet.vehicle.contract']
        task = Todo.create({'type_id':1})
        self.assertEqual(task.is_done,False)
# vim:expandtab:smartindent:tabstop=4:softtabstop=4:shiftwidth=4:

