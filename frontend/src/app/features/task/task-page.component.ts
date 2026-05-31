import { CommonModule, Location } from '@angular/common';
import { HttpErrorResponse } from '@angular/common/http';
import { Component, computed, inject, OnInit, signal } from '@angular/core';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { TaskItem } from '../../core/models/learning.models';
import { LearningService } from '../../core/services/learning.service';

@Component({
  selector: 'app-task-page',
  imports: [CommonModule, RouterLink],
  templateUrl: './task-page.component.html',
  styleUrl: './task-page.component.css'
})
export class TaskPageComponent implements OnInit {
  private readonly route = inject(ActivatedRoute);
  private readonly learningService = inject(LearningService);
  private readonly location = inject(Location);

  readonly isLoading = signal(false);
  readonly errorMessage = signal('');
  readonly task = signal<TaskItem | null>(null);
  readonly taskId = computed(() => Number(this.route.snapshot.paramMap.get('taskId')));

  ngOnInit(): void {
    this.loadTask();
  }

  goBack(): void {
    this.location.back();
  }

  private loadTask(): void {
    const taskId = this.taskId();
    if (!taskId) {
      this.errorMessage.set('Задание не найдено.');
      return;
    }

    this.isLoading.set(true);
    this.learningService.getTask(taskId).subscribe({
      next: (task) => {
        this.task.set(task);
        this.isLoading.set(false);
      },
      error: (error: HttpErrorResponse) => {
        this.errorMessage.set(error.error?.detail || 'Не удалось загрузить задание.');
        this.isLoading.set(false);
      }
    });
  }
}
