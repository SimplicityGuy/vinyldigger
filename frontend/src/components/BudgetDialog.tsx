import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from '@/components/ui/form'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import { Calendar } from '@/components/ui/calendar'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { budgetApi } from '@/lib/api'
import { useToast } from '@/hooks/useToast'
import { SearchBudget } from '@/types/api'
import { CalendarIcon, Loader2 } from 'lucide-react'
import { format } from 'date-fns'
import { cn } from '@/lib/utils'

const budgetSchema = z.object({
  monthly_limit: z.number().min(1, 'Budget must be at least $1'),
  period_start: z.date(),
  period_end: z.date(),
  is_active: z.boolean().default(true),
}).refine((data) => data.period_end > data.period_start, {
  message: 'End date must be after start date',
  path: ['period_end'],
})

interface BudgetDialogProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  existingBudget?: SearchBudget | null
}

export function BudgetDialog({ open, onOpenChange, existingBudget }: BudgetDialogProps) {
  const { toast } = useToast()
  const queryClient = useQueryClient()
  const [isLoading, setIsLoading] = useState(false)

  const form = useForm({
    resolver: zodResolver(budgetSchema),
    defaultValues: {
      monthly_limit: existingBudget?.monthly_limit || 100,
      period_start: existingBudget ? new Date(existingBudget.period_start) : new Date(),
      period_end: existingBudget ? new Date(existingBudget.period_end) : (() => {
        const nextMonth = new Date()
        nextMonth.setMonth(nextMonth.getMonth() + 1)
        return nextMonth
      })(),
      is_active: existingBudget?.is_active ?? true,
    },
  })

  const createBudgetMutation = useMutation({
    mutationFn: budgetApi.createBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-summary'] })
      queryClient.invalidateQueries({ queryKey: ['budget-alerts'] })
      queryClient.invalidateQueries({ queryKey: ['spending-analytics'] })
      toast({ title: 'Budget created successfully' })
      onOpenChange(false)
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to create budget',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const updateBudgetMutation = useMutation({
    mutationFn: ({ budgetId, data }: { budgetId: string; data: {
      monthly_limit: number
      period_start: string
      period_end: string
      is_active: boolean
    } }) =>
      budgetApi.updateBudget(budgetId, data),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-summary'] })
      queryClient.invalidateQueries({ queryKey: ['budget-alerts'] })
      queryClient.invalidateQueries({ queryKey: ['spending-analytics'] })
      toast({ title: 'Budget updated successfully' })
      onOpenChange(false)
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to update budget',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const resetBudgetMutation = useMutation({
    mutationFn: budgetApi.resetMonthlyBudget,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['budget-summary'] })
      queryClient.invalidateQueries({ queryKey: ['budget-alerts'] })
      queryClient.invalidateQueries({ queryKey: ['spending-analytics'] })
      toast({ title: 'Budget reset successfully' })
      onOpenChange(false)
    },
    onError: (error: Error) => {
      toast({
        title: 'Failed to reset budget',
        description: error.message,
        variant: 'destructive',
      })
    },
  })

  const onSubmit = async (values: z.infer<typeof budgetSchema>) => {
    setIsLoading(true)
    try {
      const budgetData = {
        monthly_limit: values.monthly_limit,
        period_start: values.period_start.toISOString(),
        period_end: values.period_end.toISOString(),
        is_active: values.is_active,
      }

      if (existingBudget) {
        updateBudgetMutation.mutate({
          budgetId: existingBudget.id,
          data: budgetData,
        })
      } else {
        createBudgetMutation.mutate(budgetData)
      }
    } finally {
      setIsLoading(false)
    }
  }

  const handleReset = () => {
    resetBudgetMutation.mutate()
  }

  const isSubmitting = isLoading || createBudgetMutation.isPending || updateBudgetMutation.isPending

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-[425px]">
        <DialogHeader>
          <DialogTitle>
            {existingBudget ? 'Edit Search Budget' : 'Set Search Budget'}
          </DialogTitle>
          <DialogDescription>
            Set a monthly limit for your search spending to control costs.
          </DialogDescription>
        </DialogHeader>

        <Form {...form}>
          <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-4">
            <FormField
              control={form.control}
              name="monthly_limit"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Monthly Limit</FormLabel>
                  <FormControl>
                    <div className="relative">
                      <span className="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground">
                        $
                      </span>
                      <Input
                        type="number"
                        step="0.01"
                        min="1"
                        className="pl-6"
                        placeholder="100.00"
                        {...field}
                        onChange={(e) => field.onChange(parseFloat(e.target.value) || 0)}
                      />
                    </div>
                  </FormControl>
                  <FormDescription>
                    Maximum amount to spend on searches per month
                  </FormDescription>
                  <FormMessage />
                </FormItem>
              )}
            />

            <div className="grid grid-cols-2 gap-4">
              <FormField
                control={form.control}
                name="period_start"
                render={({ field }) => (
                  <FormItem className="flex flex-col">
                    <FormLabel>Period Start</FormLabel>
                    <Popover>
                      <PopoverTrigger asChild>
                        <FormControl>
                          <Button
                            variant="outline"
                            className={cn(
                              'w-full pl-3 text-left font-normal',
                              !field.value && 'text-muted-foreground'
                            )}
                          >
                            {field.value ? (
                              format(field.value, 'MMM d, yyyy')
                            ) : (
                              <span>Pick a date</span>
                            )}
                            <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                          </Button>
                        </FormControl>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={field.value}
                          onSelect={field.onChange}
                          disabled={(date) =>
                            date > new Date() || date < new Date('1900-01-01')
                          }
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                    <FormMessage />
                  </FormItem>
                )}
              />

              <FormField
                control={form.control}
                name="period_end"
                render={({ field }) => (
                  <FormItem className="flex flex-col">
                    <FormLabel>Period End</FormLabel>
                    <Popover>
                      <PopoverTrigger asChild>
                        <FormControl>
                          <Button
                            variant="outline"
                            className={cn(
                              'w-full pl-3 text-left font-normal',
                              !field.value && 'text-muted-foreground'
                            )}
                          >
                            {field.value ? (
                              format(field.value, 'MMM d, yyyy')
                            ) : (
                              <span>Pick a date</span>
                            )}
                            <CalendarIcon className="ml-auto h-4 w-4 opacity-50" />
                          </Button>
                        </FormControl>
                      </PopoverTrigger>
                      <PopoverContent className="w-auto p-0" align="start">
                        <Calendar
                          mode="single"
                          selected={field.value}
                          onSelect={field.onChange}
                          disabled={(date) => date < new Date()}
                          initialFocus
                        />
                      </PopoverContent>
                    </Popover>
                    <FormMessage />
                  </FormItem>
                )}
              />
            </div>

            <FormField
              control={form.control}
              name="is_active"
              render={({ field }) => (
                <FormItem className="flex flex-row items-center justify-between rounded-lg border p-4">
                  <div className="space-y-0.5">
                    <FormLabel className="text-base">Active Budget</FormLabel>
                    <FormDescription>
                      Enable budget tracking and alerts
                    </FormDescription>
                  </div>
                  <FormControl>
                    <Switch
                      checked={field.value}
                      onCheckedChange={field.onChange}
                    />
                  </FormControl>
                </FormItem>
              )}
            />

            <DialogFooter className="flex-col sm:flex-row gap-2">
              {existingBudget && (
                <Button
                  type="button"
                  variant="outline"
                  onClick={handleReset}
                  disabled={isSubmitting || resetBudgetMutation.isPending}
                  className="w-full sm:w-auto"
                >
                  {resetBudgetMutation.isPending && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  Reset Spending
                </Button>
              )}
              <div className="flex gap-2 w-full sm:w-auto">
                <Button
                  type="button"
                  variant="outline"
                  onClick={() => onOpenChange(false)}
                  disabled={isSubmitting}
                  className="flex-1 sm:flex-none"
                >
                  Cancel
                </Button>
                <Button
                  type="submit"
                  disabled={isSubmitting}
                  className="flex-1 sm:flex-none"
                >
                  {isSubmitting && (
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  )}
                  {existingBudget ? 'Update' : 'Create'} Budget
                </Button>
              </div>
            </DialogFooter>
          </form>
        </Form>
      </DialogContent>
    </Dialog>
  )
}
